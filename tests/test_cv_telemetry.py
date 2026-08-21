from __future__ import annotations

import unittest

from cv_agent.telemetry import LLMCallUsage, PRICING_SNAPSHOT_DATE, estimate_cost_usd, summarize_usage


class TelemetryTests(unittest.TestCase):
    def test_known_model_cost_uses_cached_and_output_rates(self) -> None:
        cost = estimate_cost_usd(
            "gpt-5.6-luna",
            prompt_tokens=10_000,
            cached_input_tokens=2_000,
            candidate_tokens=1_000,
            reasoning_tokens=500,
        )
        expected = ((8_000 * 0.20) + (2_000 * 0.02) + (1_500 * 1.20)) / 1_000_000
        self.assertAlmostEqual(cost or 0.0, expected, places=8)

    def test_unknown_openai_model_is_unpriced_not_guessed(self) -> None:
        self.assertIsNone(estimate_cost_usd(
            "gpt-future",
            prompt_tokens=100,
            cached_input_tokens=0,
            candidate_tokens=50,
        ))

    def test_usage_summary_preserves_per_call_trace(self) -> None:
        calls = [
            LLMCallUsage(
                name="cv_strategist",
                model="gpt-5.6-terra",
                prompt_tokens=1_000,
                cached_input_tokens=0,
                candidate_tokens=200,
                reasoning_tokens=0,
                total_tokens=1_200,
                duration_ms=250,
                estimated_cost_usd=estimate_cost_usd(
                    "gpt-5.6-terra",
                    prompt_tokens=1_000,
                    cached_input_tokens=0,
                    candidate_tokens=200,
                ),
                pricing_snapshot_date=PRICING_SNAPSHOT_DATE,
                pricing_basis="test",
            )
        ]
        summary = summarize_usage(calls)
        self.assertEqual(summary["call_count"], 1)
        self.assertEqual(summary["total_tokens"], 1_200)
        self.assertEqual(summary["calls"][0]["name"], "cv_strategist")
        self.assertIsNotNone(summary["estimated_cost_usd"])


if __name__ == "__main__":
    unittest.main()
