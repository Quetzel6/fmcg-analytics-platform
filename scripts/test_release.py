import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from run_release import stages,certification,execute

class ReleaseTests(unittest.TestCase):
    def test_report_artifacts_precede_full_tests(self):
        names=[name for name,args in stages(True)];self.assertLess(names.index('risk_report'),names.index('all_tests'));self.assertIn('load',names)
        self.assertNotIn('load',[n for n,a in stages(False)])
    def test_skips_rejected_for_database_certification(self):
        summary=dict(status='passed',tests=76,passed=74,skipped=2)
        self.assertEqual(certification(summary,False),'passed_local_database_pending')
        with self.assertRaises(ValueError):certification(summary,True)
        with self.assertRaises(ValueError):certification(dict(status='passed',tests=76,passed=75,skipped=2),False)
    def test_missing_database_blocks_before_any_process(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{},clear=True):
            result=execute(root=Path(tmp),run=lambda *a,**k:self.fail('Must not run a process'))
            self.assertEqual(result['status'],'blocked')
    def test_failure_stops_later_stages(self):
        calls=[]
        def run(args,**kwargs):calls.append(args);return subprocess.CompletedProcess(args,1,'','failed')
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(local=True,root=Path(tmp),run=run,check=lambda root:dict(status='ready'));self.assertEqual(result['status'],'failed');self.assertEqual(len(calls),1)
    def test_local_mode_cannot_use_inherited_database(self):
        def run(args,**kwargs):
            self.assertNotIn('FMCG_TEST_DATABASE_URL',kwargs['env']);self.assertNotIn('DATABASE_URL',kwargs['env']);return subprocess.CompletedProcess(args,1,'','')
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'FMCG_TEST_DATABASE_URL':'private-db','DATABASE_URL':'private-db'}):
            self.assertFalse(execute(local=True,root=Path(tmp),run=run)['database_verified'])

    def test_bad_environment_blocks_without_launching_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(local=True,root=Path(tmp),
                run=lambda *a,**k:self.fail('Must not launch a stage'),
                check=lambda root:dict(status='blocked',reason='Python too old'))
            self.assertEqual(result['status'],'blocked')
            self.assertFalse(result['database_verified'])
            self.assertEqual(result['stages'],[])
            self.assertEqual(result['reason'],'Python too old')
            self.assertIn('finished_utc',result)

if __name__=='__main__':unittest.main()
