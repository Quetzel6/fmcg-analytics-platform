"""Offline orchestration tests; these do not certify PostgreSQL."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from accept_postgres import execute,require_completed_tests

class AcceptanceTests(unittest.TestCase):
    def test_skip_and_incomplete_rejected(self):
        self.assertTrue(require_completed_tests('Ran 2 tests in 1s\n\nOK\n',0))
        for text,code in [('Ran 2 tests\nOK (skipped=2)\n',0),('Ran 1 test\nOK\n',0),('Ran 2 tests\nOK\n',1),('OK\n',0)]:self.assertFalse(require_completed_tests(text,code))
    def test_missing_docker_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            result=execute(Path(temp),docker=lambda _:None)
            self.assertEqual(result['status'],'blocked');self.assertFalse(result['database_verified']);self.assertTrue((Path(temp)/'latest.json').exists())
    def test_missing_client_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            def run(args,**kwargs):return subprocess.CompletedProcess(args,1,'','')
            result=execute(Path(temp),run=run,dependency=lambda _:None,docker=lambda _:'docker');self.assertEqual(result['status'],'blocked')
    def test_unowned_container_never_removed(self):
        calls=[]
        def run(args,**kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args,0,'someone-else' if 'inspect' in args else '', '')
        with tempfile.TemporaryDirectory() as temp:execute(Path(temp),run=run,dependency=lambda _:None,docker=lambda _:'docker')
        self.assertFalse(any('rm' in args for args in calls))
    def test_engine_unavailable(self):
        def run(args,**kwargs):return subprocess.CompletedProcess(args,1,'','')
        with tempfile.TemporaryDirectory() as temp:
            result=execute(Path(temp),run=run,dependency=lambda _:True,docker=lambda _:'docker');self.assertEqual(result['status'],'blocked')


class LifecycleTests(unittest.TestCase):
    def run_fixture(self,log='Ran 2 tests in 1s\n\nOK\n'):
        calls=[];state={}
        def run(args,**kwargs):
            calls.append(args)
            if 'run' in args:
                state['token']=args[args.index('--label')+1].split('=',1)[1]
            if 'inspect' in args:return subprocess.CompletedProcess(args,0,state.get('token','')+'\n','')
            if 'port' in args:return subprocess.CompletedProcess(args,0,'127.0.0.1:55432\n','')
            if 'unittest' in args:return subprocess.CompletedProcess(args,0,'',log)
            if 'fmcg.load' in args:
                Path(args[-1]).write_text(json.dumps(dict(status='committed',post_load=dict(status='passed'))))
            return subprocess.CompletedProcess(args,0,'','')
        return calls,run
    def test_successful_owned_lifecycle(self):
        calls,run=self.run_fixture()
        with tempfile.TemporaryDirectory() as temp:
            result=execute(Path(temp),run=run,dependency=lambda _:True,docker=lambda _:'docker')
            self.assertEqual(result['status'],'passed');self.assertEqual(result['cleanup'],'removed')
        started=next(c for c in calls if 'run' in c);self.assertIn('127.0.0.1::5432',started);self.assertIn('--env-file',started)
        self.assertTrue(any('rm' in c for c in calls))
    def test_skips_fail_and_still_clean_up(self):
        calls,run=self.run_fixture('Ran 2 tests\nOK (skipped=2)\n')
        with tempfile.TemporaryDirectory() as temp:
            result=execute(Path(temp),run=run,dependency=lambda _:True,docker=lambda _:'docker')
            self.assertEqual(result['status'],'failed');self.assertFalse(result['database_verified']);self.assertEqual(result['cleanup'],'removed')
        self.assertFalse(any('fmcg.load' in c for c in calls))
    def test_exception_after_start_cleans_up(self):
        calls,original=self.run_fixture()
        def run(args,**kwargs):
            if 'pg_isready' in args:raise subprocess.TimeoutExpired(args,10)
            return original(args,**kwargs)
        with tempfile.TemporaryDirectory() as temp:
            result=execute(Path(temp),run=run,dependency=lambda _:True,docker=lambda _:'docker')
            self.assertEqual(result['status'],'failed');self.assertEqual(result['cleanup'],'removed')

if __name__=='__main__':unittest.main()
