from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_handoff.builder import build_handoffs, rebuild_index


class WorkHandoffTests(unittest.TestCase):
    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_builder_creates_diagnostic_evidence_grounded_public_safe_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_id = "vac-demo"
            run_id = "run-1"
            outputs = root / "outputs"
            run_dir = outputs / vacancy_id / run_id
            vacancy_state = root / "vacancy_state"
            handoff = root / "handoff"
            template = root / "technical_modern_v1.html.j2"
            identity = root / "identity.public.yaml"
            evidence_state = root / "rag_state"
            generation_manifest = root / "generation_state" / "manifest.json"

            template.write_text("<html>{{ cv }}</html>", encoding="utf-8")
            identity.write_text("name: Public Candidate\nlinkedin: https://example.com/in/public\n", encoding="utf-8")

            self._write_json(vacancy_state / "records" / f"{vacancy_id}.json", {
                "vacancy_id": vacancy_id,
                "company": "Example Co",
                "role_title": "Senior Data Scientist",
                "url": "https://example.com/jobs/1",
                "fit_score": 97,
                "fit_strengths": ["Strong Python and ML alignment"],
                "fit_gaps": ["No direct evidence for Kubeflow"],
                "tech_stack": ["Python", "Kubeflow"],
                "jd_fidelity": "full",
                "description": "<p>Build <strong>production</strong> data science systems.</p><p>Lead delivery.</p>",
                "requirements": ["Python", "ML"],
                "responsibilities": ["Own models"],
                "email": "private@example.com",
                "posted_date": "2026-08-27",
                "provenance": [{"source_search_date": "2026-08-27"}],
            })
            self._write_json(run_dir / "cv_final.json", {
                "best_review_iteration": 2,
                "quality_note": "Below target.",
                "quality_target_reached": False,
                "cv": {
                    "headline": "Senior Data Scientist",
                    "email": "private@example.com",
                    "summary": {
                        "text": "Grounded summary",
                        "evidence_refs": ["role-demo::summary"],
                    },
                    "experience": [{
                        "company": "BBVA",
                        "phone": "555",
                        "bullets": [{
                            "text": "Built ML systems",
                            "evidence_refs": ["role-demo::summary"],
                        }],
                    }],
                },
            })
            self._write_json(run_dir / "run_report.json", {
                "match_coverage_score": 73.5,
                "final_review": {
                    "overall_score": 81,
                    "decision": "REVISE",
                    "blocking_issues": ["Make leadership evidence more explicit"],
                },
                "final_validation": {"factual": {"status": "PASS"}},
            })
            (run_dir / "cv_primary.html").write_text("<html>proposal</html>", encoding="utf-8")
            (run_dir / "cv_final.md").write_text("# Senior Data Scientist\n\nGrounded summary.", encoding="utf-8")
            (run_dir / "cover_letter_final.md").write_text("Dear Hiring Team", encoding="utf-8")
            self._write_json(run_dir / "match_plan.json", {
                "coverage_score": 73.5,
                "requirements": [
                    {"requirement": "Python", "coverage": "supported"},
                    {"requirement": "Kubeflow", "coverage": "unsupported"},
                ],
                "selected_evidence_chunk_ids": [
                    "role-demo::summary",
                    "role-demo::opportunity",
                ],
            })
            self._write_json(run_dir / "application_bundle_report.json", {
                "ready_to_send": False,
                "reasons": ["content_quality_target_not_reached"],
                "templates": [{
                    "role": "primary",
                    "html_file": "cv_primary.html",
                }],
            })
            self._write_json(generation_manifest, {
                "entries": {
                    vacancy_id: {
                        "headhunter_score": 81,
                        "headhunter_decision": "REVISE",
                        "headhunter_iterations": 3,
                        "best_review_iteration": 2,
                        "coverage_score": 73.5,
                        "unsupported_requirements": ["Kubeflow"],
                        "content_quality_target_reached": False,
                        "presentation_gate": {
                            "status": "REVIEW_REQUIRED",
                            "reasons": ["content_quality_target_not_reached"],
                        },
                    }
                }
            })
            self._write_json(evidence_state / "chunks" / "role-demo.json", {
                "chunks": [{
                    "chunk_id": "role-demo::summary",
                    "title": "Role summary",
                    "text": "Built production ML systems with Python.",
                    "constraints": ["Do not claim Kubeflow."],
                    "confidence": "high",
                    "proficiency": None,
                    "source_path": "experience/roles/demo.md",
                    "record_type": "role",
                    "chunk_type": "role_detail",
                    "metric_refs": [],
                    "public_safe": True,
                }, {
                    "chunk_id": "role-demo::opportunity",
                    "title": "Opportunity evidence",
                    "text": "Led production pipeline quality and safe automation.",
                    "constraints": ["Do not claim people management."],
                    "confidence": "high",
                    "proficiency": None,
                    "source_path": "experience/roles/demo.md",
                    "record_type": "role",
                    "chunk_type": "role_detail",
                    "metric_refs": [],
                    "public_safe": True,
                }]
            })
            batch = root / "batch.json"
            self._write_json(batch, {
                "results": [{
                    "vacancy_id": vacancy_id,
                    "run_id": run_id,
                    "status": "REVIEW_REQUIRED",
                }]
            })

            report = build_handoffs(
                batch_report=batch,
                outputs=outputs,
                vacancy_state=vacancy_state,
                template_file=template,
                handoff_dir=handoff,
                generation_manifest=generation_manifest,
                evidence_state=evidence_state,
                public_identity=identity,
                repository="jcval94/CV_fit",
            )

            self.assertEqual(report["built"], [vacancy_id])
            package = handoff / vacancy_id
            for name in (
                "review_context.json",
                "match_plan.json",
                "evidence_snapshot.json",
                "vacancy.md",
                "vacancy.json",
                "cv_proposed.json",
                "cv_proposed.md",
                "cv_proposed.html",
                "html_base.html.j2",
                "public_identity.yaml",
                "cover_letter_proposed.md",
                "prompt.md",
                "handoff.json",
            ):
                self.assertTrue((package / name).exists(), name)

            proposed = json.loads((package / "cv_proposed.json").read_text(encoding="utf-8"))
            vacancy = json.loads((package / "vacancy.json").read_text(encoding="utf-8"))
            manifest = json.loads((package / "handoff.json").read_text(encoding="utf-8"))
            context = json.loads((package / "review_context.json").read_text(encoding="utf-8"))
            evidence = json.loads((package / "evidence_snapshot.json").read_text(encoding="utf-8"))
            match_plan = json.loads((package / "match_plan.json").read_text(encoding="utf-8"))
            index = json.loads((handoff / "index.json").read_text(encoding="utf-8"))
            vacancy_md = (package / "vacancy.md").read_text(encoding="utf-8")

            self.assertNotIn("email", proposed["cv"])
            self.assertNotIn("phone", proposed["cv"]["experience"][0])
            self.assertNotIn("email", vacancy)
            self.assertNotIn("<strong>", vacancy_md)
            self.assertIn("Build production data science systems.", vacancy_md)
            self.assertEqual(context["quality_kpi"], 81)
            self.assertEqual(context["evidence_coverage"]["unsupported_requirements"], ["Kubeflow"])
            self.assertEqual(context["headhunter"]["decision"], "REVISE")
            self.assertEqual(evidence["resolved_ref_count"], 2)
            self.assertEqual(evidence["proposal_refs"], ["role-demo::summary"])
            self.assertEqual(evidence["opportunity_refs"], ["role-demo::opportunity"])
            evidence_by_id = {item["chunk_id"]: item for item in evidence["evidence"]}
            self.assertEqual(evidence_by_id["role-demo::summary"]["constraints"], ["Do not claim Kubeflow."])
            self.assertEqual(evidence_by_id["role-demo::opportunity"]["constraints"], ["Do not claim people management."])
            self.assertEqual(match_plan["requirements"][1]["coverage"], "unsupported")
            self.assertIn("Grounded summary", (package / "cv_proposed.md").read_text(encoding="utf-8"))
            self.assertEqual(manifest["quality_kpi"], 81)
            self.assertEqual(manifest["status"], "pending_final_review")
            self.assertEqual(manifest["contact_policy"], "public_safe_only_in_repo")
            self.assertEqual(manifest["source_fit"], 97)
            self.assertIn("review_context.json", (package / "prompt.md").read_text(encoding="utf-8"))
            self.assertEqual(index["pending_count"], 1)
            self.assertEqual(index["schema_version"], 2)

    def test_empty_batch_refreshes_existing_package_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff"
            package = handoff / "vac-existing"
            evidence_state = root / "rag_state"
            package.mkdir(parents=True)

            self._write_json(package / "handoff.json", {
                "vacancy_id": "vac-existing",
                "company": "Existing",
                "source_fit": 90,
                "status": "pending_final_review",
                "schema_version": 1,
                "files": {},
            })
            self._write_json(package / "cv_proposed.json", {
                "cv": {
                    "summary": {
                        "text": "Current claim",
                        "evidence_refs": ["role-demo::used"],
                    }
                }
            })
            self._write_json(package / "match_plan.json", {
                "selected_evidence_chunk_ids": [
                    "role-demo::used",
                    "role-demo::opportunity",
                ]
            })
            self._write_json(evidence_state / "chunks" / "role-demo.json", {
                "chunks": [
                    {
                        "chunk_id": "role-demo::used",
                        "title": "Used",
                        "text": "Used evidence",
                        "constraints": [],
                        "confidence": "high",
                        "public_safe": True,
                    },
                    {
                        "chunk_id": "role-demo::opportunity",
                        "title": "Opportunity",
                        "text": "Opportunity evidence",
                        "constraints": ["Do not overclaim."],
                        "confidence": "high",
                        "public_safe": True,
                    },
                ]
            })
            batch = root / "batch.json"
            self._write_json(batch, {"results": []})

            report = build_handoffs(
                batch_report=batch,
                outputs=root / "outputs",
                vacancy_state=root / "vacancy_state",
                template_file=root / "missing-template.j2",
                handoff_dir=handoff,
                generation_manifest=root / "missing-generation.json",
                evidence_state=evidence_state,
                public_identity=root / "missing-identity.yaml",
                repository="jcval94/CV_fit",
            )

            self.assertEqual(report["built"], [])
            self.assertEqual(report["refreshed_existing"], ["vac-existing"])
            snapshot = json.loads((package / "evidence_snapshot.json").read_text(encoding="utf-8"))
            manifest = json.loads((package / "handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(snapshot["proposal_refs"], ["role-demo::used"])
            self.assertEqual(snapshot["opportunity_refs"], ["role-demo::opportunity"])
            self.assertEqual(snapshot["resolved_ref_count"], 2)
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["files"]["evidence_snapshot"], "evidence_snapshot.json")
            self.assertIn("opportunity_refs", (package / "prompt.md").read_text(encoding="utf-8"))

    def test_existing_final_html_is_preserved_as_finalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            handoff = Path(tmp) / "handoff"
            package = handoff / "vac-existing"
            package.mkdir(parents=True)
            (package / "final.html").write_text("<html>final</html>", encoding="utf-8")
            self._write_json(package / "handoff.json", {
                "vacancy_id": "vac-existing",
                "company": "Existing",
                "source_fit": 90,
                "status": "finalized",
            })
            payload = rebuild_index(handoff)
            self.assertEqual(payload["finalized_count"], 1)
            self.assertEqual(payload["pending_count"], 0)

    def test_pending_queue_uses_fit_then_most_recent_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            handoff = Path(tmp) / "handoff"
            for vacancy_id, fit, date in (
                ("older-high", 95, "2026-08-20"),
                ("newer-high", 95, "2026-08-27"),
                ("newer-low", 90, "2026-08-28"),
            ):
                package = handoff / vacancy_id
                package.mkdir(parents=True)
                self._write_json(package / "handoff.json", {
                    "vacancy_id": vacancy_id,
                    "company": vacancy_id,
                    "source_fit": fit,
                    "source_date": date,
                    "status": "pending_final_review",
                })
            payload = rebuild_index(handoff)
            order = [row["vacancy_id"] for row in payload["candidates"]]
            self.assertEqual(order, ["newer-high", "older-high", "newer-low"])


if __name__ == "__main__":
    unittest.main()
