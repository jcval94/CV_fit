from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cv_agent.model_policy import model_ids, policy_for_iteration
from cv_agent.openai_provider import prepare_openai_environment, validate_openai_model_id


class OpenAIProviderTests(unittest.TestCase):
    def test_default_model_policy_uses_openai_gpt56_family(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            for name in (
                "CV_FIT_MODEL_ECONOMY",
                "CV_FIT_MODEL_BALANCED",
                "CV_FIT_MODEL_PREMIUM",
            ):
                os.environ.pop(name, None)
            self.assertEqual(
                model_ids(),
                {
                    "economy": "gpt-5.6-luna",
                    "balanced": "gpt-5.6-terra",
                    "premium": "gpt-5.6-sol",
                },
            )
            self.assertEqual(policy_for_iteration(5).reviewer_model, "gpt-5.6-sol")

    def test_non_openai_model_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_openai_model_id("gemini-3.6-flash")
        with self.assertRaises(ValueError):
            validate_openai_model_id("anthropic/claude-sonnet")
        self.assertEqual(validate_openai_model_id("gpt-5.6-terra"), "gpt-5.6-terra")

    def test_repo_key_name_is_mirrored_only_in_process(self) -> None:
        with patch.dict(os.environ, {"OPENAI_APY_KEY": "test-openai-key"}, clear=True):
            value = prepare_openai_environment(required=True)
            self.assertEqual(value, "test-openai-key")
            self.assertEqual(os.environ["OPENAI_API_KEY"], "test-openai-key")

    def test_missing_repo_key_fails_live_preflight(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                prepare_openai_environment(required=True)


if __name__ == "__main__":
    unittest.main()
