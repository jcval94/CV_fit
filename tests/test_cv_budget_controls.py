from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cv_auto import AUTO_GENERATION_LOGIC_VERSION
from cv_auto.runner import run_generation_batch


class FakeGenerator:
    def __init__(self, cost: float = 0.42) -> None:
        self.cost = cost
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        return (
            {
                "status": "PASS",
                "quality_target_reached": True,
                "match_coverage_score": 90,
                "unsupported_requirements": [],
            },
            {"estimated_cost_usd": self.cost, "known_estimated_cost_usd": self.cost},
        )


class GenerationBudgetControlTests(unittest.TestCase):
    def _write(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _fixture(self, root: Path):
        vacancy_state = root / "vacancy_state"
        evidence_state = root / "rag_state"
        generation_state = root / "generation_state"
        outputs = root / "outputs"
        for name, payload in {
            "manifest.json": {"pipeline_version": 1},
            "lexical_index.json": {"chunks": {}},
            "dense_index.json": {"chunks": {}},
            "relations.json": {"relations": []},
        }.items():
            self._write(evidence_state / name, payload)
        return vacancy_state, evidence_state, generation_state, outputs

    def _vacancy(self, state: Path, vacancy_id: str, content_hash: str) -> None:
        self._write(state / "records" / f"{vacancy_id}.json", {
            "vacancy_id": vacancy_id,
            "content_hash": content_hash,
            "application_language": "es",
            "jd_generation_eligible": True,
            "jd_fidelity": "full",
            "jd_fidelity_score": 100,
            "jd_fidelity_reasons": [],
        })

    def test_global_batch_budget_stops_starting_additional_cvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            for index in range(1, 4):
                self._vacancy(vacancy_state, f"vac-{index}", f"h{index}")
            generator = FakeGenerator(cost=0.42)
            report = run_generation_batch(
                candidate_ids=["vac-1", "vac-2", "vac-3"],
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                generation_state=generation_state,
                outputs=outputs,
                run_id="test",
                source_commit="abc",
                max_vacancies_per_run=6,
                max_estimated_cost_usd=2.0,
                max_batch_estimated_cost_usd=0.6,
                min_batch_remaining_usd=0.25,
                generator=generator,
            )
            self.assertEqual(report["generation_attempts"], 1)
            self.assertAlmostEqual(report["batch_known_spend_usd"], 0.42)
            self.assertEqual(report["result_counts"].get("DEFERRED_BUDGET"), 2)
            self.assertEqual(len(generator.calls), 1)
            self.assertAlmostEqual(generator.calls[0]["max_estimated_cost_usd"], 0.6)

    def test_new_candidates_are_ahead_of_deferred_backlog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-new", "new")
            self._vacancy(vacancy_state, "vac-old", "old")
            evidence_hash_placeholder = "legacy"
            self._write(generation_state / "manifest.json", {
                "pipeline_version": 1,
                "entries": {"vac-old": {
                    "status": "DEFERRED_CAP",
                    "generation_logic_version": AUTO_GENERATION_LOGIC_VERSION,
                    "fingerprint": "old",
                    "evidence_fingerprint": evidence_hash_placeholder,
                }},
            })
            generator = FakeGenerator()
            run_generation_batch(
                candidate_ids=["vac-new"],
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                generation_state=generation_state,
                outputs=outputs,
                run_id="test",
                source_commit="abc",
                max_vacancies_per_run=1,
                max_estimated_cost_usd=2.0,
                generator=generator,
            )
            self.assertEqual(generator.calls[0]["vacancy_id"], "vac-new")

    def test_paid_backlog_can_be_disabled_when_no_new_candidate_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vacancy_state, evidence_state, generation_state, outputs = self._fixture(root)
            self._vacancy(vacancy_state, "vac-old", "old")
            self._write(generation_state / "manifest.json", {
                "pipeline_version": 1,
                "entries": {"vac-old": {"status": "DEFERRED_CAP", "generation_logic_version": AUTO_GENERATION_LOGIC_VERSION - 1}},
            })
            generator = FakeGenerator()
            report = run_generation_batch(
                candidate_ids=[],
                vacancy_state=vacancy_state,
                evidence_state=evidence_state,
                generation_state=generation_state,
                outputs=outputs,
                run_id="test",
                source_commit="abc",
                max_vacancies_per_run=6,
                max_estimated_cost_usd=2.0,
                include_stale_logic=False,
                process_deferred_without_candidates=False,
                generator=generator,
            )
            self.assertEqual(report["generation_attempts"], 0)
            self.assertEqual(generator.calls, [])


if __name__ == "__main__":
    unittest.main()
