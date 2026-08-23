from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cv_presentation.application_bundle import _design_for_template
from cv_presentation.design_agent import DesignReview


class _DesignClient:
    async def call(self, **kwargs):
        return DesignReview(
            decision="PASS",
            preserve_template=False,
            ats_safe=True,
            print_safe=True,
            notes=["Neutral fallback is readable and ATS-safe."],
        )


class PresentationFallbackBrandTests(unittest.TestCase):
    def test_new_company_without_brand_yaml_uses_neutral_safe_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            tokens, review, deterministic = _design_for_template(
                client=_DesignClient(),
                template_id="technical_modern_v1",
                company="Brand New Employer",
                brand_profiles_dir=Path(tmp),
            )
        self.assertFalse(tokens.brand_verified)
        self.assertEqual(tokens.brand_source_kind, "fallback")
        self.assertTrue(deterministic.passed)
        self.assertEqual(review.decision, "PASS")


if __name__ == "__main__":
    unittest.main()
