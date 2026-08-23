import json
import tempfile
import unittest
from pathlib import Path

from cv_observability.production_canary import build_summary


class ProductionCanaryContractTests(unittest.TestCase):
    def test_public_issue_trigger_is_not_allowed(self):
        workflow = Path('.github/workflows/production-canary.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('\n  issues:', workflow)
        self.assertNotIn("github.event.issue.title", workflow)
        self.assertNotIn("gh issue comment", workflow)

    def test_semantic_failure_overrides_successful_process_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / 'outputs'
            generation_state = root / 'generation_state'
            vacancy_id = 'vac-demo'
            run_id = 'canary-1'
            batch_dir = outputs / '_batch' / run_id
            batch_dir.mkdir(parents=True)
            generation_state.mkdir(parents=True)

            (batch_dir / 'generation_run_report.json').write_text(
                json.dumps({
                    'results': [{
                        'vacancy_id': vacancy_id,
                        'run_id': 'generated-1',
                        'status': 'FAILED_REVIEW_REQUIRED',
                        'error': 'RateLimitError: credit_balance_exhausted',
                    }]
                }),
                encoding='utf-8',
            )
            (generation_state / 'manifest.json').write_text(
                json.dumps({'entries': {vacancy_id: {'run_id': 'generated-1', 'status': 'FAILED_REVIEW_REQUIRED'}}}),
                encoding='utf-8',
            )

            summary = build_summary(
                outputs_root=outputs,
                generation_state=generation_state,
                vacancy_id=vacancy_id,
                canary_run_id=run_id,
                process_outcomes={
                    'retrieval': 'success',
                    'generation': 'success',
                    'cover': 'success',
                    'presentation': 'success',
                },
            )

            self.assertFalse(summary['canary_healthy'])
            self.assertEqual(summary['process_outcomes']['generation'], 'success')
            self.assertEqual(summary['stage_outcomes']['generation'], 'FAILED_REVIEW_REQUIRED')
            self.assertEqual(summary['stage_outcomes']['cover'], 'NOT_REACHED')
            self.assertEqual(summary['stage_outcomes']['presentation'], 'NOT_REACHED')
            self.assertIn('cover_letter_final.md', summary['missing_artifacts'])

    def test_happy_path_requires_real_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / 'outputs'
            generation_state = root / 'generation_state'
            vacancy_id = 'vac-demo'
            canary_run_id = 'canary-1'
            generated_run_id = 'generated-1'
            batch_dir = outputs / '_batch' / canary_run_id
            run_dir = outputs / vacancy_id / generated_run_id
            batch_dir.mkdir(parents=True)
            run_dir.mkdir(parents=True)
            generation_state.mkdir(parents=True)

            (batch_dir / 'generation_run_report.json').write_text(
                json.dumps({'results': [{'vacancy_id': vacancy_id, 'run_id': generated_run_id, 'status': 'PASS'}]}),
                encoding='utf-8',
            )
            (batch_dir / 'application_bundle_batch_report.json').write_text(
                json.dumps({'results': [{'vacancy_id': vacancy_id, 'status': 'PASS', 'ready_to_send': True}]}),
                encoding='utf-8',
            )
            (generation_state / 'manifest.json').write_text(
                json.dumps({'entries': {vacancy_id: {'run_id': generated_run_id, 'status': 'PASS'}}}),
                encoding='utf-8',
            )
            for name in (
                'cv_final.json',
                'cover_letter_final.md',
                'cv_primary.html',
                'cv_primary.pdf',
                'application_bundle_report.json',
            ):
                (run_dir / name).write_text('artifact', encoding='utf-8')

            summary = build_summary(
                outputs_root=outputs,
                generation_state=generation_state,
                vacancy_id=vacancy_id,
                canary_run_id=canary_run_id,
                process_outcomes={
                    'retrieval': 'success',
                    'generation': 'success',
                    'cover': 'success',
                    'presentation': 'success',
                },
            )

            self.assertTrue(summary['canary_healthy'])
            self.assertEqual(summary['stage_outcomes'], {
                'retrieval': 'PASS',
                'generation': 'PASS',
                'cover': 'PASS',
                'presentation': 'PASS',
            })
            self.assertEqual(summary['missing_artifacts'], [])


if __name__ == '__main__':
    unittest.main()
