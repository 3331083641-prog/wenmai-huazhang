"""Exercise the real worker subprocess without models, credentials or network."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import interactive_jobs


class InteractiveWorkerEnvironmentTests(unittest.TestCase):
    def run_worker(self, offline):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            script = Path(folder) / 'worker.py'
            script.write_text("import os\nprint('AUDIT_OFFLINE='+os.getenv('HF_HUB_OFFLINE','unset'))\n", encoding='utf-8')
            with patch.dict(os.environ, dict(os.environ), clear=True):
                os.environ.pop('HF_HUB_OFFLINE', None)
                if offline is not None:
                    os.environ['HF_HUB_OFFLINE'] = offline
                with patch.object(interactive_jobs, 'INGEST_SCRIPT', script), patch.object(
                    interactive_jobs, '_read_artifacts', return_value={'hasExperience': True, 'hasWorld': True}
                ), patch.object(interactive_jobs, '_update') as update:
                    interactive_jobs._run('audit-worker', 20)
                    finished = update.call_args.kwargs
            self.assertEqual(finished['status'], 'ready')
            return finished['tail']

    def test_background_worker_uses_local_models_by_default(self):
        self.assertIn('AUDIT_OFFLINE=1', self.run_worker(None))

    def test_explicit_model_download_preference_is_preserved(self):
        self.assertIn('AUDIT_OFFLINE=0', self.run_worker('0'))

    def test_failed_rebuild_does_not_claim_stale_assets_are_ready(self):
        import subprocess
        with patch.object(interactive_jobs, '_read_artifacts', return_value={'hasExperience': True, 'hasWorld': True}), patch.object(
            interactive_jobs.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'vision unavailable')
        ), patch.object(interactive_jobs, '_update') as update:
            interactive_jobs._run('audit-worker', 20)
        self.assertEqual(update.call_args.kwargs['status'], 'failed')

    def test_timeout_does_not_claim_stale_assets_are_ready(self):
        import subprocess
        with patch.object(interactive_jobs, '_read_artifacts', return_value={'hasExperience': True, 'hasWorld': True}), patch.object(
            interactive_jobs.subprocess, 'run', side_effect=subprocess.TimeoutExpired('worker', 20)
        ), patch.object(interactive_jobs, '_update') as update:
            interactive_jobs._run('audit-worker', 20)
        self.assertEqual(update.call_args.kwargs['status'], 'failed')

    def test_api_reports_failed_rebuild_before_old_assets(self):
        from app import _interaction_summary
        result = _interaction_summary({'hasExperience': True, 'hasWorld': True}, {'status': 'failed'})
        self.assertEqual(result['status'], 'failed')

    def test_force_retry_reuses_active_job_to_prevent_concurrent_writers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            (Path(folder)/'audit-worker').mkdir()
            active={'caseId':'audit-worker','status':'processing','attempts':1}
            with patch.object(interactive_jobs,'_load'), patch.object(interactive_jobs,'EXAMPLES_DIR',Path(folder)), patch.dict(
                interactive_jobs._JOBS,{'audit-worker':active},clear=True
            ), patch.object(interactive_jobs,'_save_locked'), patch.object(interactive_jobs.threading,'Thread') as thread:
                result=interactive_jobs.start_interactive_build('audit-worker',force=True)
            self.assertTrue(result['reused'])
            thread.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
