import datetime as dt
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from run_candidate import execute, PAGES


class CandidateTests(unittest.TestCase):
    def runner(self, root, local=True, fail=None, stale=False, verified=True, missing=False):
        def run(args, **kwargs):
            name = 'default_release' if 'scripts/run_release.py' in args else args[-1].split('.')[-1]
            if local:
                self.assertNotIn('DATABASE_URL', kwargs['env']); self.assertNotIn('FMCG_TEST_DATABASE_URL', kwargs['env'])
            output=root/'output'
            if name == 'default_release':
                started=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=1 if stale else 0)
                (output/'release_status.json').write_text(json.dumps(dict(
                    status='passed_local_database_pending' if local else 'passed', database_verified=verified,
                    started_utc=started.isoformat(), tests=dict(status='passed',tests=76,passed=76,skipped=0))))
            if name == 'q4_plan' and not missing:
                for _, path in PAGES:
                    p=output/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('new page')
            return subprocess.CompletedProcess(args, 1 if name==fail else 0, 'fixture', '')
        return run

    def test_local_success_never_certifies_or_inherits_database(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',dict(DATABASE_URL='secret',FMCG_TEST_DATABASE_URL='secret')):
            root=Path(tmp); result=execute(True,root,self.runner(root))
            self.assertEqual(result['status'],'passed_local_database_pending'); self.assertFalse(result['database_verified'])
            self.assertEqual(len(result['stages']),4)
            self.assertTrue((root/'output/release_candidate.html').exists())

    def test_supplement_failure_stops_and_removes_old_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'output').mkdir(); (root/'output/release_candidate.html').write_text('old')
            result=execute(True,root,self.runner(root,fail='receipt_scenario'))
            self.assertEqual(result['status'],'failed'); self.assertEqual(len(result['stages']),3)
            self.assertFalse((root/'output/release_candidate.html').exists())

    def test_stale_default_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); result=execute(True,root,self.runner(root,stale=True))
            self.assertEqual(result['status'],'failed'); self.assertEqual(len(result['stages']),1)

    def test_database_mode_requires_verified_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); result=execute(False,root,self.runner(root,local=False,verified=False))
            self.assertEqual(result['status'],'failed')

    def test_successful_process_without_pages_cannot_publish_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); result=execute(True,root,self.runner(root,missing=True))
            self.assertEqual(result['status'],'failed'); self.assertNotIn('pages',result)

    def test_verified_database_mode_preserves_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); result=execute(False,root,self.runner(root,local=False))
            self.assertEqual(result['status'],'passed'); self.assertTrue(result['database_verified'])

    def test_build_input_change_during_run_removes_success_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); runner=self.runner(root)
            def changing_runner(args, **kwargs):
                (root/'requirements.txt').write_text('changed while building')
                return runner(args, **kwargs)
            result=execute(True,root,changing_runner)
            self.assertEqual(result['status'],'failed')
            self.assertIn('inputs changed',result['reason'])
            self.assertFalse((root/'output/release_candidate.html').exists())


if __name__ == '__main__': unittest.main()
