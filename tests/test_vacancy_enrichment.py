from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vacancy_pipeline.enrich import enrich_repo, extract_matching_job_posting, job_posting_fields
from vacancy_pipeline.fidelity import assess_jd_fidelity


JOB_HTML = '''
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Senior Data Scientist II",
  "hiringOrganization": {"@type": "Organization", "name": "LexisNexis"},
  "description": "<p>Own end-to-end machine learning and generative AI solutions from problem framing through experimentation, deployment, evaluation and continuous improvement. Build robust Python services, retrieval augmented generation systems, agentic workflows, embeddings and vector search capabilities in collaboration with product and engineering stakeholders. This role is accountable for production quality, model behavior, hallucination evaluation, observability and business outcomes.</p><p>The successful candidate works across applied research and production delivery, communicates tradeoffs clearly and improves systems using measurable evidence.</p>",
  "qualifications": "<ul><li>Professional experience building machine learning or AI systems in Python and cloud environments.</li><li>Hands-on experience with LLMs, RAG, embeddings, vector search and agentic workflows.</li><li>Strong software engineering practices including testing, version control and production monitoring.</li></ul>",
  "responsibilities": "<ul><li>Lead AI projects from scoping and experimentation through production deployment and evaluation.</li><li>Design and improve retrieval and agentic systems with explicit quality and hallucination metrics.</li><li>Partner with product and engineering teams to deliver reliable business outcomes.</li></ul>"
}
</script></head><body>Job</body></html>
'''


class VacancyEnrichmentTests(unittest.TestCase):
    def test_extracts_matching_jobposting_and_preserves_generation_eligible_detail(self):
        node = extract_matching_job_posting(JOB_HTML, role_title="Senior Data Scientist II", company="LexisNexis")
        self.assertIsNotNone(node)
        fields = job_posting_fields(node or {})
        self.assertGreaterEqual(len(fields["description"] or ""), 300)
        self.assertGreaterEqual(len(fields["requirements"]), 3)
        self.assertGreaterEqual(len(fields["responsibilities"]), 3)
        assessment = assess_jd_fidelity(
            description=fields["description"],
            requirements=fields["requirements"],
            responsibilities=fields["responsibilities"],
        )
        self.assertTrue(assessment.generation_eligible)

    def test_daily_sparse_vacantes_feed_creates_derived_enrichment_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / "Vacantes" / "vacantes_2026-08-23.json"
            source.parent.mkdir(parents=True)
            payload = {
                "metadata": {"fecha_busqueda": "2026-08-23", "total_vacantes_encontradas": 1},
                "vacantes": [{
                    "id_vacante": "4456047445",
                    "puesto": "Senior Data Scientist II",
                    "empresa": "LexisNexis",
                    "ubicacion": "Ciudad de México, México",
                    "modalidad": "Remoto",
                    "fecha_publicacion": "2026-08-21",
                    "porcentaje_ajuste": 96,
                    "url_postulacion": "https://example.test/jobs/4456047445"
                }]
            }
            source.write_text(json.dumps(payload), encoding="utf-8")
            original_text = source.read_text(encoding="utf-8")

            report = enrich_repo(
                repo=repo,
                report_path=repo / "report.json",
                max_fetches=2,
                fetcher=lambda url: JOB_HTML,
            )
            self.assertEqual(report["written"], 1)
            self.assertEqual(source.read_text(encoding="utf-8"), original_text)
            outputs = list((repo / "Vacantes" / "enriched" / "auto").glob("*.json"))
            self.assertEqual(len(outputs), 1)
            enriched = json.loads(outputs[0].read_text(encoding="utf-8"))
            row = enriched["vacantes"][0]
            self.assertEqual(row["empresa"], "LexisNexis")
            self.assertGreaterEqual(len(row["description"]), 300)
            self.assertEqual(enriched["jd_capture_mode"], "official_source_jsonld_jobposting_auto")

            second = enrich_repo(
                repo=repo,
                report_path=repo / "report2.json",
                max_fetches=2,
                fetcher=lambda url: JOB_HTML,
            )
            self.assertEqual(second["written"], 0)
            self.assertTrue(any(item["status"] == "ALREADY_ENRICHED" for item in second["results"]))

    def test_non_matching_jobposting_is_not_attached_to_vacancy(self):
        node = extract_matching_job_posting(JOB_HTML, role_title="Chief Financial Officer", company="Different Company")
        self.assertIsNone(node)


if __name__ == "__main__":
    unittest.main()
