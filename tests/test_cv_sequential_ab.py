from __future__ import annotations

import unittest

from cv_agent.sequential_ab import (
    _representative_sequence,
    _sequential_stop_reason,
    _should_run_second_audit,
)


def _case(
    *,
    savings: float = 35.0,
    delta: int = 0,
    machine_gate: bool = True,
    validators_pass: bool = True,
    consensus: str = "optimized",
) -> dict:
    return {
        "optimized": {"validators_pass": validators_pass},
        "comparison": {
            "cost_savings_pct": savings,
            "headhunter_score_delta": delta,
            "machine_gate_pass": machine_gate,
        },
        "agent_audit": {"consensus": consensus},
    }


class SequentialSamplingTests(unittest.TestCase):
    def test_representative_sequence_starts_at_median_then_extremes(self) -> None:
        candidates = [
            {"vacancy_id": "low", "coverage": 0.20},
            {"vacancy_id": "mid", "coverage": 0.60},
            {"vacancy_id": "high", "coverage": 0.95},
        ]
        selected = _representative_sequence(candidates, 3)
        self.assertEqual([item["vacancy_id"] for item in selected], ["mid", "low", "high"])

    def test_single_strong_positive_case_stops_experiment(self) -> None:
        self.assertEqual(
            _sequential_stop_reason([_case()]),
            "strong_positive_after_one_representative_case",
        )

    def test_single_ambiguous_case_requires_more_evidence(self) -> None:
        self.assertIsNone(
            _sequential_stop_reason([
                _case(savings=26.0, delta=-2, machine_gate=True, consensus="tie")
            ])
        )

    def test_two_positive_cases_stop_before_third(self) -> None:
        self.assertEqual(
            _sequential_stop_reason([
                _case(savings=27.0, delta=-1),
                _case(savings=31.0, delta=0, consensus="tie"),
            ]),
            "confirmed_positive_after_two_cases",
        )

    def test_two_decisive_negative_cases_stop_before_third(self) -> None:
        self.assertEqual(
            _sequential_stop_reason([
                _case(savings=8.0, delta=-4, machine_gate=False, consensus="baseline"),
                _case(savings=15.0, delta=-3, machine_gate=False, consensus="baseline"),
            ]),
            "confirmed_not_promising_after_two_cases",
        )


class AdaptiveAuditTests(unittest.TestCase):
    def test_high_confidence_positive_skips_second_paid_audit(self) -> None:
        self.assertFalse(
            _should_run_second_audit(
                first_winner="optimized",
                first_confidence=90,
                savings_pct=36.0,
                score_delta=0,
                optimized_safe=True,
            )
        )

    def test_ambiguous_positive_keeps_order_reversed_second_audit(self) -> None:
        self.assertTrue(
            _should_run_second_audit(
                first_winner="optimized",
                first_confidence=71,
                savings_pct=36.0,
                score_delta=0,
                optimized_safe=True,
            )
        )

    def test_high_confidence_baseline_win_skips_second_audit_when_metrics_are_bad(self) -> None:
        self.assertFalse(
            _should_run_second_audit(
                first_winner="baseline",
                first_confidence=93,
                savings_pct=7.0,
                score_delta=-5,
                optimized_safe=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
