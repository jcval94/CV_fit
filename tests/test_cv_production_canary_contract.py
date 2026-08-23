from pathlib import Path
import unittest


class ProductionCanaryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = Path('.github/workflows/production-canary.yml').read_text(encoding='utf-8')
        cls.diagnostic = Path('cv_observability/production_canary.py').read_text(encoding='utf-8')

    def test_canary_starts_from_versioned_retrieval_v2_and_refreshes_dense_state(self):
        self.assertIn('cp -a rag_state /tmp/rag_state', self.workflow)
        self.assertIn('python -m rag.evidence', self.workflow)
        self.assertIn('python -m rag.dense --state-dir /tmp/rag_state', self.workflow)
        for filename in ('manifest.json', 'lexical_index.json', 'dense_index.json', 'relations.json'):
            self.assertIn(filename, self.workflow)

    def test_failures_still_produce_structured_diagnostics(self):
        self.assertIn('id: retrieval', self.workflow)
        self.assertIn('id: generation', self.workflow)
        self.assertIn('id: cover', self.workflow)
        self.assertIn('id: presentation', self.workflow)
        self.assertIn('Build structured E2E diagnostic', self.workflow)
        self.assertIn('RETRIEVAL_OUTCOME:', self.workflow)
        self.assertIn('python -m cv_observability.production_canary', self.workflow)
        self.assertIn('"canary_healthy": canary_healthy', self.diagnostic)
        self.assertIn('"process_outcomes": process', self.diagnostic)
        self.assertIn('"stage_outcomes": stage_outcomes', self.diagnostic)
        self.assertGreaterEqual(self.workflow.count('if: always()'), 4)

    def test_public_issue_cannot_trigger_paid_canary(self):
        self.assertIn('workflow_dispatch:', self.workflow)
        self.assertNotIn('\n  issues:', self.workflow)
        self.assertNotIn('github.event.issue', self.workflow)
        self.assertNotIn('gh issue comment', self.workflow)
        self.assertNotIn('issues: write', self.workflow)

    def test_whatsapp_is_not_part_of_canary(self):
        self.assertNotIn('cv_notifications.whatsapp', self.workflow)
        self.assertNotIn('WHATSAPP_ACCESS_TOKEN', self.workflow)
        self.assertNotIn('WHATSAPP_NOTIFICATIONS_ENABLED', self.workflow)


if __name__ == '__main__':
    unittest.main()
