"""Rebuild all reports and fail closed before certifying a release."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
from doctor import check_environment
ROOT=Path(__file__).resolve().parents[1]

def stages(database):
    plan=[('generate',['-m','fmcg.generate']),('quality',['-m','fmcg.validate','--strict-sanity'])]
    if database:plan.append(('load',['-m','fmcg.load']))
    for name in ['report','dashboard','forecast_report','forecast_dashboard','promotion_report','promotion_dashboard','risk_report','risk_dashboard']:
        plan.append((name,['-m','fmcg.'+name]))
    plan.extend([('demo',['scripts/build_demo.py']),('helper_tests',['-m','unittest','discover','-s','scripts','-p','test_*.py','-v']),('all_tests',['tests/run_all.py'])])
    return plan

def certification(summary,require_database):
    if summary.get('status')!='passed' or not summary.get('tests') or summary.get('passed',0)+summary.get('skipped',0)!=summary['tests']:raise ValueError('Missing or inconsistent complete test evidence')
    if require_database and summary['skipped']:raise ValueError('Database release cannot contain skipped tests')
    return 'passed' if require_database else 'passed_local_database_pending'

def execute(local=False,run=subprocess.run,root=ROOT,check=check_environment):
    output=root/'output';output.mkdir(parents=True,exist_ok=True)
    result=dict(status='running',database_verified=False,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),stages=[])
    environment=dict(os.environ,PYTHONPATH=str(root/'src'))
    url=environment.get('FMCG_TEST_DATABASE_URL')
    if local:
        # Local mode never connects to an incidental database inherited from the shell.
        environment.pop('FMCG_TEST_DATABASE_URL',None);environment.pop('DATABASE_URL',None)
    elif not url:
        result.update(status='blocked',reason='FMCG_TEST_DATABASE_URL must identify a dedicated disposable database')
        (output/'release_status.json').write_text(json.dumps(result,indent=2)+'\n');return result
    else:environment['DATABASE_URL']=url
    preflight=check(root)
    result['environment']=preflight
    if preflight['status']!='ready':
        result.update(status='blocked',reason=preflight['reason'],finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        (output/'release_status.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    try:
        for name,arguments in stages(not local):
            print('Running release stage: '+name,flush=True)
            completed=run([sys.executable,*arguments],cwd=root,env=environment,capture_output=True,text=True)
            text=completed.stdout+completed.stderr
            if url:
                text=text.replace(url,'[dedicated database]');password=urlparse(url).password
                if password:text=text.replace(password,'[redacted]')
            (output/('release_'+name+'.txt')).write_text(text)
            result['stages'].append(dict(name=name,returncode=completed.returncode,status='passed' if completed.returncode==0 else 'failed'))
            if completed.returncode:raise ValueError('Stage failed: '+name)
        summary=json.loads((output/'test_summary.json').read_text());result['status']=certification(summary,not local);result['tests']=summary
        if not local:
            load=json.loads((output/'load_report.json').read_text())
            if load.get('status')!='committed' or load.get('post_load',{}).get('status')!='passed':raise ValueError('Missing committed database reconciliation')
            result['database_verified']=True
    except (ValueError,OSError) as error:result.update(status='failed',reason=str(error) if isinstance(error,ValueError) else 'Local process or file operation failed')
    except KeyboardInterrupt:result.update(status='interrupted',reason='Release interrupted')
    finally:
        result['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();(output/'release_status.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--local',action='store_true',help='Rebuild locally without connecting to a database; cannot certify database release');a=p.parse_args()
    result=execute(a.local);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status'] in ('passed','passed_local_database_pending') else 2)
