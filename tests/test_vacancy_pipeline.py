from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vacancy_pipeline.contract import VacancyValidationError, adapt_source_document
from vacancy_pipeline.index import retrieve
from vacancy_pipeline.pipeline import run_pipeline
from vacancy_pipeline.trace import RecommendationTrace, validate_trace


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def gptw_doc(*, fit: int = 95, title: str = "AI/ML Engineer Sr.") -> dict:
    return {
        "last_updated": "2026-08-21T13:58:05Z",
        "total_results": 1,
        "vacancies": [{
            "id": "konfio-ai-ml-engineer-sr-2026-08-18",
            "company": "Konfío",
            "role_title": title,
            "seniority": "Senior",
            "tech_stack": ["Python", "Machine Learning", "LLMs", "MLOps"],
            "location": {"city": "Ciudad de México", "work_model": "Hybrid"},
            "posted_date": "2026-08-18",
            "url": "[https://jobs.example.com/konfio/123?utm_source=test](https://jobs.example.com/konfio/123?utm_source=test)",
            "fit_score": fit,
            "fit_evaluation": "Strong fit for production AI and financial services."
        }]
    }


def vacantes_doc() -> dict:
    return {
        "metadata": {"fecha_busqueda": "2026-08-21", "total_vacantes_encontradas": 1},
        "vacantes": [{
            "id_vacante": "payjoy-1",
            "puesto": "Machine Learning Engineer - Fraud",
            "empresa": "PayJoy",
            "categoria_empresa": "Fintech",
            "ubicacion": "Mexico City, CDMX",
            "modalidad": "Híbrido",
            "fecha_publicacion": "Hace 1 semana",
            "porcentaje_ajuste": 96,
            "razon_ajuste": {
                "puntos_fuertes": ["Fraud and credit-risk production ML."],
                "posibles_gaps": ["Some infrastructure depth may be required."],
                "resumen": "Excellent fraud/risk alignment."
            },
            "stack_clave_detectado": ["Machine Learning", "Fraud detection", "Python", "SQL"],
            "rango_salarial": "No especificado",
            "url_postulacion": "https://jobs.example.com/payjoy/fraud-1"
        }]
    }


class ContractTests(unittest.TestCase):
    def test_adapters_create_common_model_and_clean_urls(self) -> None:
        record = adapt_source_document(gptw_doc(), "GPTW/a.json", "abc")[0]
        self.assertEqual(record.company, "Konfío")
        self.assertEqual(record.work_model, "Hybrid")
        self.assertEqual(record.url, "https://jobs.example.com/konfio/123")
        self.assertTrue(record.vacancy_id.startswith("vac-"))
        self.assertEqual(record.provenance[0].source_native_id, "konfio-ai-ml-engineer-sr-2026-08-18")

    def test_same_opening_from_two_formats_deduplicates_by_identity(self) -> None:
        gptw = gptw_doc()
        gptw["vacancies"][0]["company"] = "PayJoy"
        gptw["vacancies"][0]["role_title"] = "Machine Learning Engineer - Fraud"
        gptw["vacancies"][0]["location"]["city"] = "Mexico City, CDMX"
        a = adapt_source_document(gptw, "GPTW/a.json", "a")[0]
        b = adapt_source_document(vacantes_doc(), "Vacantes/b.json", "b")[0]
        self.assertEqual(a.vacancy_id, b.vacancy_id)

    def test_invalid_count_is_rejected_atomically(self) -> None:
        doc = gptw_doc()
        doc["total_results"] = 2
        with self.assertRaises(VacancyValidationError):
            adapt_source_document(doc, "GPTW/a.json", "abc")


class IncrementalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.state = self.repo / "vacancy_state"
        write_json(self.repo / "GPTW" / "a.json", gptw_doc())
        write_json(self.repo / "Vacantes" / "b.json", vacantes_doc())

    def test_incremental_idempotent_processing_and_reindex(self) -> None:
        first = run_pipeline(self.repo, self.state, run_id="run-1")
        self.assertEqual(first["source_counts"]["new"], 2)
        self.assertEqual(first["vacancy_counts"]["active"], 2)
        self.assertEqual(first["vacancy_counts"]["reindexed"], 2)

        second = run_pipeline(self.repo, self.state, run_id="run-2")
        self.assertEqual(second["source_counts"]["unchanged"], 2)
        self.assertEqual(second["vacancy_counts"]["impacted"], 0)
        self.assertEqual(second["vacancy_counts"]["reindexed"], 0)

        changed = gptw_doc(fit=90)
        changed["vacancies"][0]["fit_evaluation"] = "Updated fit assessment."
        write_json(self.repo / "GPTW" / "a.json", changed)
        third = run_pipeline(self.repo, self.state, run_id="run-3")
        self.assertEqual(third["source_counts"]["modified"], 1)
        self.assertEqual(third["source_counts"]["unchanged"], 1)
        self.assertEqual(third["vacancy_counts"]["impacted"], 1)
        self.assertEqual(third["vacancy_counts"]["reindexed"], 1)

    def test_invalid_modified_file_is_quarantined_and_removed_from_active_state(self) -> None:
        run_pipeline(self.repo, self.state, run_id="good")
        bad = gptw_doc()
        bad["vacancies"][0].pop("company")
        write_json(self.repo / "GPTW" / "a.json", bad)
        report = run_pipeline(self.repo, self.state, run_id="bad")
        self.assertEqual(report["status"], "completed_with_quarantine")
        self.assertEqual(report["source_counts"]["quarantined"], 1)
        self.assertEqual(report["vacancy_counts"]["active"], 1)
        self.assertTrue(list((self.state / "quarantine").glob("*current.errors.json")))

    def test_deleted_source_removes_only_affected_vacancy(self) -> None:
        run_pipeline(self.repo, self.state, run_id="before")
        (self.repo / "GPTW" / "a.json").unlink()
        report = run_pipeline(self.repo, self.state, run_id="after")
        self.assertEqual(report["source_counts"]["deleted"], 1)
        self.assertEqual(report["vacancy_counts"]["active"], 1)
        self.assertEqual(report["vacancy_counts"]["deleted"], 1)


class RetrievalAndTraceTests(unittest.TestCase):
    def test_retrieval_and_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            state = repo / "vacancy_state"
            write_json(repo / "Vacantes" / "b.json", vacantes_doc())
            run_pipeline(repo, state, run_id="e2e")
            index = json.loads((state / "lexical_index.json").read_text(encoding="utf-8"))
            hits = retrieve(index, "fraud Python machine learning", top_k=3)
            self.assertTrue(hits)
            self.assertEqual(hits[0].source_paths, ["Vacantes/b.json"])

            evidence = [{
                "record_id": "project-bbva-fraud-detection",
                "source_path": "experience/projects/fraud_detection.md",
            }]
            trace = RecommendationTrace(
                vacancy_id=hits[0].vacancy_id,
                vacancy_chunk_ids=[hits[0].chunk_id],
                vacancy_source_paths=["Vacantes/b.json"],
                evidence_record_ids=["project-bbva-fraud-detection"],
                evidence_source_paths=["experience/projects/fraud_detection.md"],
            )
            validate_trace(trace, index, evidence)


if __name__ == "__main__":
    unittest.main()
