from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_agent.cost_optimized import run_cost_optimized_cv
from cv_agent.model_policy import cost_optimized_policy_for_iteration
from tests.test_cv_agent_workflow import FakeClient, catalog_fixture, context_fixture, make_review


class CostOptimizedPolicyTests(unittest.TestCase):
    def test_fifth_review_stays_balanced_when_not_close_to_pass(self) -> None:
        policy = cost_optimized_policy_for_iteration(
            5,
            previous_score=87,
            previous_blocking_issues=2,
            previous_validators_pass=True,
        )
        self.assertEqual(policy.tier, "balanced_guarded")
        self.assertFalse(policy.premium)

    def test_fifth_review_preserves_premium_when_close_to_pass(self) -> None:
        policy = cost_optimized_policy_for_iteration(
            5,
            previous_score=91,
            previous_blocking_issues=1,
            previous_validators_pass=True,
        )
        self.assertEqual(policy.tier, "premium")
        self.assertTrue(policy.premium)


class CostOptimizedWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_stagnation_stops_after_three_safe_reviews(self) -> None:
        client = FakeClient([make_review(88), make_review(89), make_review(89)])
        with tempfile.TemporaryDirectory() as temp, patch(
            "cv_agent.cost_optimized.assemble_application_context",
            return_value=context_fixture(),
        ), patch(
            "cv_agent.cost_optimized.load_evidence_catalog",
            return_value=catalog_fixture(),
        ):
            report = await run_cost_optimized_cv(
                vacancy_id="vac-test",
                client=client,
                output_dir=Path(temp),
                run_id="cost-stagnation",
            )

        self.assertEqual(report["status"], "COMPLETED_BELOW_TARGET")
        self.assertEqual(report["iterations_executed"], 3)
        self.assertEqual(report["early_stop_reason"], "stagnant_quality_after_three_reviews")
        self.assertFalse(report["premium_model_used"])
        reviewers = [call for call in client.calls if call["name"].startswith("senior_headhunter_")]
        revisers = [call for call in client.calls if call["name"].startswith("cv_reviser_")]
        self.assertEqual(len(reviewers), 3)
        self.assertEqual(len(revisers), 2)
        self.assertLess(len(client.calls), 11)

    async def test_early_pass_matches_baseline_behavior(self) -> None:
        client = FakeClient([make_review(97, "PASS")])
        with tempfile.TemporaryDirectory() as temp, patch(
            "cv_agent.cost_optimized.assemble_application_context",
            return_value=context_fixture(),
        ), patch(
            "cv_agent.cost_optimized.load_evidence_catalog",
            return_value=catalog_fixture(),
        ):
            report = await run_cost_optimized_cv(
                vacancy_id="vac-test",
                client=client,
                output_dir=Path(temp),
                run_id="cost-pass",
            )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["iterations_executed"], 1)
        self.assertIsNone(report["early_stop_reason"])


if __name__ == "__main__":
    unittest.main()
