from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_auto import AUTO_GENERATION_LOGIC_VERSION
from cv_auto.runner import candidate_ids_from_ingest_report, run_generation_batch


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        return (
            {
                "status": "PASS",
                "quality_target_reached": True,
                "match_coverage_score": 88.0,
                "unsupported_requirements": [],
            },
            {"estimated_cost_usd": 0.42},
        )


class AutomaticGenerationTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _fixture(self, root: Path):
        vacancy_state = root / "vacancy_state"
        evidence_state = root / "rag_state"
        generation_state = root / "generation_state"
        outputs = root / "outputs"
        for name, payload in {
            "manifest.json": {"pipeline_version": 1, "sources": {}},
            "lexical_index.json": {"chunks": {}, "record_chunks": {}},
            "dense_index.json": {"model": "fake", "dimensions": 3, "chunks": {}},
            "relations.json": {"relations": []},
        }.items():
            self._write_json(evidence_state / name, payload)
        return vacancy_state, evidence_state, generation_state, outputs

    def _vacancy(self, state: Path, vacancy_id: str, content_hash: str, *, eligible: bool = True):
        payload = {
            "vacancy_id": vacancy_id,
            "content_hash": content_hash,
            "application_language": "es",
            "jd_generation_eligible": eligible,
            "jd_fidelity": "full" if eligible else "sparse",
            "jd_fidelity_score": 100 if eligible else 20,
            "jd_fidelity_reasons": [] if eligible else ["missing employer requirements"],
        }
        self._write_json(state / "records" / f"{vacancy_id}.json", payload)

    def _run(self, *, ids, vacancy_state, evidence_state, generation_state, outputs, generator, max_vacancies=5):
        return run_generation_batch(
            candidate_ids=ids,
            vacancy_state=vacancy_state,
            evidence_state=evidence_state,
            generation_state=generation_state,
            outputs=outputs,
            run_id="test-run",
            source_commit="abc123",
            retrieval_mode="hybrid-rerank",
            max_vacancies_per_run=max_vacancies,
            max_estimated_cost_usd=2.0,
            generator=generator,
        )

    def test_same_fingerprint_is_generated_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-1", "h1")
            generator = FakeGenerator()

            first = self._run(
                ids=["vac-1"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                generation_state=generation_state, outputs=outputs, generator=generator,
            )
            second = self._run(
                ids=["vac-1"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                generation_state=generation_state, outputs=outputs, generator=generator,
            )
            self.assertEqual(first["generation_attempts"], 1)
            self.assertEqual(second["generation_attempts"], 0)
            self.assertEqual(second["results"][0]["status"], "SKIPPED_IDEMPOTENT")
            self.assertEqual(len(generator.calls), 1)
            manifest = json.loads((generation_state / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["entries"]["vac-1"]["ready_to_send"])
            self.assertEqual(manifest["entries"]["vac-1"]["generation_logic_version"], AUTO_GENERATION_LOGIC_VERSION)

    def test_changed_vacancy_hash_generates_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-1", "h1")
            generator = FakeGenerator()
            self._run(ids=["vac-1"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                      generation_state=generation_state, outputs=outputs, generator=generator)
            self._vacancy(vacancy_state, "vac-1", "h2")
            self._run(ids=["vac-1"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                      generation_state=generation_state, outputs=outputs, generator=generator)
            self.assertEqual(len(generator.calls), 2)

    def test_generation_logic_change_requeues_terminal_entry_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-1", "h1")
            generator = FakeGenerator()
            self._run(ids=["vac-1"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                      generation_state=generation_state, outputs=outputs, generator=generator)

            manifest_path = generation_state / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["entries"]["vac-1"]["generation_logic_version"] = AUTO_GENERATION_LOGIC_VERSION - 1
            manifest["entries"]["vac-1"]["fingerprint"] = "legacy-fingerprint"
            self._write_json(manifest_path, manifest)

            reprocessed = self._run(ids=[], vacancy_state=vacancy_state, evidence_state=evidence_state,
                                    generation_state=generation_state, outputs=outputs, generator=generator)
            settled = self._run(ids=[], vacancy_state=vacancy_state, evidence_state=evidence_state,
                                generation_state=generation_state, outputs=outputs, generator=generator)
            self.assertEqual(reprocessed["stale_logic_candidate_count"], 1)
            self.assertEqual(reprocessed["generation_attempts"], 1)
            self.assertEqual(settled["stale_logic_candidate_count"], 0)
            self.assertEqual(settled["generation_attempts"], 0)
            self.assertEqual(len(generator.calls), 2)

    def test_sparse_jd_is_persistently_skipped_without_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-sparse", "h1", eligible=False)
            generator = FakeGenerator()
            report = self._run(ids=["vac-sparse"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                               generation_state=generation_state, outputs=outputs, generator=generator)
            self.assertEqual(report["results"][0]["status"], "SKIPPED_NOT_ELIGIBLE")
            self.assertEqual(generator.calls, [])
            manifest = json.loads((generation_state / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["entries"]["vac-sparse"]["status"], "SKIPPED_NOT_ELIGIBLE")

    def test_capacity_deferred_candidate_is_processed_on_next_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-1", "h1")
            self._vacancy(vacancy_state, "vac-2", "h2")
            generator = FakeGenerator()
            first = self._run(ids=["vac-1", "vac-2"], vacancy_state=vacancy_state, evidence_state=evidence_state,
                              generation_state=generation_state, outputs=outputs, generator=generator, max_vacancies=1)
            self.assertEqual(first["result_counts"].get("DEFERRED_CAP"), 1)
            second = self._run(ids=[], vacancy_state=vacancy_state, evidence_state=evidence_state,
                               generation_state=generation_state, outputs=outputs, generator=generator, max_vacancies=1)
            self.assertEqual(second["generation_attempts"], 1)
            self.assertEqual(len(generator.calls), 2)

    def test_ingest_report_supplies_only_reindexed_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            self._write_json(path, {"reindexed_vacancy_ids": ["vac-a", "vac-b"], "deleted_vacancy_ids": ["vac-z"]})
            self.assertEqual(candidate_ids_from_ingest_report(path), ["vac-a", "vac-b"])


if __name__ == "__main__":
    unittest.main()
