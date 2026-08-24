from __future__ import annotations

import unittest

from cv_agent.editorial_policy import validate_editorial_policy
from cv_agent.style_contract import RULE_BY_CODE, collect_style_advisories, validate_resume_style
from tests.test_cv_editorial_policy import line, valid_cv


class ResumeStyleContractTests(unittest.TestCase):
    def assert_style_code(self, cv, code: str) -> None:
        result = validate_resume_style(cv)
        self.assertEqual(result.status, "FAIL")
        self.assertIn(code, {issue.code for issue in result.issues})

    def test_clean_resume_voice_passes(self) -> None:
        result = validate_resume_style(valid_cv())
        self.assertEqual(result.status, "PASS", result.issues)

    def test_third_person_candidate_voice_is_blocked(self) -> None:
        cv = valid_cv()
        cv.summary = line("He leads data science and AI initiatives across business environments.")
        self.assert_style_code(cv, "third_person_candidate_voice")

    def test_spanish_third_person_candidate_voice_is_blocked(self) -> None:
        cv = valid_cv()
        cv.language = "es"
        cv.summary = line("El candidato lidera iniciativas de ciencia de datos e inteligencia artificial.")
        self.assert_style_code(cv, "third_person_candidate_voice")

    def test_explicit_first_person_is_blocked(self) -> None:
        cv = valid_cv()
        cv.experience[0].bullets[0] = line("I led analytical and AI initiatives with governed delivery.")
        self.assert_style_code(cv, "explicit_first_person_pronoun")

    def test_weak_responsibility_opener_is_blocked(self) -> None:
        cv = valid_cv()
        cv.experience[0].bullets[0] = line("Responsible for analytical and AI initiatives with governed delivery.")
        self.assert_style_code(cv, "weak_responsibility_opener")

    def test_summary_over_70_words_is_blocked(self) -> None:
        cv = valid_cv()
        cv.summary = line(" ".join(["impact"] * 71))
        self.assert_style_code(cv, "summary_too_long")

    def test_bullet_over_38_words_is_blocked(self) -> None:
        cv = valid_cv()
        cv.experience[0].bullets[0] = line(" ".join(["delivered"] + ["impact"] * 38) + ".")
        self.assert_style_code(cv, "bullet_too_long")

    def test_mixed_punctuation_in_same_role_is_blocked(self) -> None:
        cv = valid_cv()
        cv.experience[0].bullets = [
            line("Led analytical and AI initiatives with governed delivery."),
            line("Built production analytics for business decisions"),
        ]
        self.assert_style_code(cv, "mixed_bullet_punctuation")

    def test_repeated_leading_verbs_are_advisory_not_blocking(self) -> None:
        cv = valid_cv()
        cv.experience[0].bullets = [line("Led analytics delivery."), line("Led AI delivery.")]
        cv.experience[1].bullets = [line("Led model delivery.")]
        self.assertEqual(validate_resume_style(cv).status, "PASS")
        advisories = collect_style_advisories(cv)
        self.assertTrue(any(issue.code == "repeated_leading_verb" for issue in advisories))

    def test_editorial_gate_includes_style_contract(self) -> None:
        cv = valid_cv()
        cv.summary = line("The candidate leads analytical delivery and AI initiatives.")
        result = validate_editorial_policy(cv)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any(issue.code == "third_person_candidate_voice" for issue in result.issues))

    def test_rule_ownership_is_explicit(self) -> None:
        third_person = RULE_BY_CODE["third_person_candidate_voice"]
        self.assertEqual(third_person.primary_owner, "writer")
        self.assertEqual(third_person.repair_owner, "reviser")
        self.assertEqual(third_person.severity, "hard")

        content_priority = RULE_BY_CODE["content_priority"]
        self.assertEqual(content_priority.primary_owner, "strategist")
        self.assertEqual(content_priority.severity, "advisory")


if __name__ == "__main__":
    unittest.main()
