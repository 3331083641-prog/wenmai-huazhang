"""Deleting a runtime case removes its public assets while preserving recovery."""
import json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import case_store,interactive_jobs


class CaseDeletionTests(unittest.TestCase):
    def make_case(self,root,origin='runtime'):
        case=root/'docs/examples/own-case';world=root/'frontend/public/interactive/own-case'
        case.mkdir(parents=True);world.mkdir(parents=True)
        (case/'metadata.json').write_text(json.dumps({'caseOrigin':origin}),encoding='utf-8')
        (case/'generated.png').write_bytes(b'local-deletion-test-only')
        (world/'world.json').write_text('{}',encoding='utf-8')
        return case,world

    def test_runtime_case_and_world_leave_public_paths_and_are_recoverable(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);case,world=self.make_case(root)
            with patch.object(case_store,'PROJECT_ROOT',root),patch.object(case_store,'EXAMPLES_DIR',root/'docs/examples'):
                self.assertTrue(case_store.archive_runtime_case('own-case'))
            self.assertFalse(case.exists());self.assertFalse(world.exists())
            self.assertEqual(len(list((root/'.cache/deleted_cases').glob('*/case/generated.png'))),1)
            self.assertEqual(len(list((root/'.cache/deleted_cases').glob('*/interactive/world.json'))),1)

    def test_curated_cases_and_path_traversal_are_protected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);case,world=self.make_case(root,'curated')
            with patch.object(case_store,'PROJECT_ROOT',root),patch.object(case_store,'EXAMPLES_DIR',root/'docs/examples'):
                self.assertFalse(case_store.archive_runtime_case('own-case'))
                self.assertFalse(case_store.archive_runtime_case('../own-case'))
            self.assertTrue(case.exists());self.assertTrue(world.exists())

    def test_active_build_cannot_be_deleted(self):
        with patch.object(interactive_jobs,'_load'),patch.object(interactive_jobs,'_save_locked'),patch.dict(
            interactive_jobs._JOBS,{'own-case':{'status':'processing'}},clear=True):
            with self.assertRaises(interactive_jobs.InteractiveJobBusy):
                with interactive_jobs.idle_case_mutation('own-case'):self.fail('must not mutate active case')
