"""Run actual PostgreSQL acceptance in an owned disposable Docker container."""
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
TESTS=['test_m1.PostgreSQLIntegration.test_snapshot_repeat_and_transaction_rollback','test_m2.PostgreSQLM2Tests.test_sql_views_match_local_results']

def require_completed_tests(text,returncode):
    import re
    return returncode==0 and re.search(r'Ran 2 tests\b',text) is not None and re.search(r'^OK$',text,re.M) is not None and 'skipped' not in text.lower()

def execute(output,run=subprocess.run,dependency=importlib.util.find_spec,docker=shutil.which):
    token=uuid.uuid4().hex;name='fmcg-accept-'+token;folder=output/token;folder.mkdir(parents=True)
    summary=dict(status='running',run_id=token,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),database_verified=False,tests=TESTS)
    password=secrets.token_hex(24);url=None
    def command(args,env=None,timeout=120):
        result=run(args,env=env,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        return result
    try:
        if not docker('docker'):summary.update(status='blocked',reason='Docker CLI is unavailable');return summary
        if not dependency('psycopg'):summary.update(status='blocked',reason='Install requirements.txt in the active Python environment');return summary
        if command(['docker','info'],timeout=30).returncode:summary.update(status='blocked',reason='Docker engine is not running');return summary
        with tempfile.TemporaryDirectory(prefix='fmcg-pg-') as temporary:
            envfile=Path(temporary)/'postgres.env';envfile.write_text('POSTGRES_DB=fmcg_accept\nPOSTGRES_USER=fmcg_accept\nPOSTGRES_PASSWORD='+password+'\n');envfile.chmod(0o600)
            started=command(['docker','run','-d','--name',name,'--label','fmcg.acceptance.run='+token,'--publish','127.0.0.1::5432','--env-file',str(envfile),'postgres:16'],timeout=300)
            if started.returncode:raise RuntimeError('Could not start dedicated PostgreSQL 16 container')
        deadline=time.monotonic()+90
        while command(['docker','exec',name,'pg_isready','-U','fmcg_accept','-d','fmcg_accept'],timeout=10).returncode:
            if time.monotonic()>deadline:raise RuntimeError('PostgreSQL readiness timed out')
            time.sleep(1)
        port=command(['docker','port',name,'5432/tcp']).stdout.strip()
        if not port.startswith('127.0.0.1:') or not port.split(':')[-1].isdigit():raise RuntimeError('Unexpected database port binding')
        url='postgresql://fmcg_accept:'+password+'@127.0.0.1:'+port.split(':')[-1]+'/fmcg_accept'
        environment=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')]),DATABASE_URL=url,FMCG_TEST_DATABASE_URL=url)
        tests=command([sys.executable,'-m','unittest',*TESTS,'-v'],env=environment,timeout=600)
        log=(tests.stdout+tests.stderr).replace(url,'[temporary database]').replace(password,'[redacted]');(folder/'integration_tests.txt').write_text(log)
        if not require_completed_tests(log,tests.returncode):raise RuntimeError('Integration tests failed, skipped or incomplete; inspect integration_tests.txt')
        loaded=command([sys.executable,'-m','fmcg.load','--report',str(folder/'load_report.json')],env=environment,timeout=300)
        if loaded.returncode:raise RuntimeError('Final snapshot load failed')
        report=json.loads((folder/'load_report.json').read_text())
        if report.get('status')!='committed' or report.get('post_load',{}).get('status')!='passed':raise RuntimeError('Missing successful database reconciliation evidence')
        summary.update(status='passed',database_verified=True,passed=2,skipped=0,load_report='load_report.json')
    except (RuntimeError,subprocess.TimeoutExpired) as error:
        summary.update(status='failed',reason=str(error) if isinstance(error,RuntimeError) else 'Command timed out')
    except OSError:
        summary.update(status="failed",reason="Local process or file operation failed")
    except KeyboardInterrupt:
        summary.update(status="interrupted",reason="Acceptance interrupted by user")
    finally:
        # Cleanup is limited to the run-labelled container this script owns.
        if docker('docker'):
            try:
                owned=command(['docker','inspect','--format','{{index .Config.Labels "fmcg.acceptance.run"}}',name],timeout=10)
                if owned.returncode==0 and owned.stdout.strip()==token:
                    removed=command(['docker','rm','-f','-v',name],timeout=30)
                    summary['cleanup']='removed' if removed.returncode==0 else 'failed; remove container '+name
            except (subprocess.TimeoutExpired,OSError):summary['cleanup']='could not finish; inspect container '+name
        summary['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');output.mkdir(parents=True,exist_ok=True)
        (output/'latest.json').write_text(json.dumps(dict(summary,report_directory=str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else str(folder)),indent=2)+'\n')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'output/postgres_acceptance');args=parser.parse_args()
    result=execute(args.output);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='passed' else 2)
