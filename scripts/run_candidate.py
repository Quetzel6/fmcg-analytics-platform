"""Rebuild the default release and supplemental scenarios as one candidate."""
import argparse
import datetime as dt
from html import escape
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = [('Default M2–M5 demo', 'index.html'),
         ('Staggered promotion benchmark', 'scenarios/staggered-v1/benchmark.html'),
         ('Reserved receipt-risk benchmark', 'scenarios/receipts-v1/benchmark.html'),
         ('Q4 commercial review', 'scenarios/q4-plan-v1/cockpit.html'),
         ('Q4 ledger and assumptions', 'scenarios/q4-plan-v1/benchmark.html')]


def execute(local=False, root=ROOT, run=subprocess.run):
    output = root/'output'; output.mkdir(parents=True, exist_ok=True)
    start = dt.datetime.now(dt.timezone.utc)
    result = dict(status='running', database_verified=False, started_utc=start.isoformat(), stages=[])
    status_path = output/'candidate_status.json'
    status_path.write_text(json.dumps(result, indent=2)+'\n')
    # Remove the old navigation entry so a failed attempt cannot leave a success page.
    entry = output/'release_candidate.html'; entry.unlink(missing_ok=True)
    env = dict(os.environ, PYTHONPATH=str(root/'src'))
    if local:
        env.pop('DATABASE_URL', None); env.pop('FMCG_TEST_DATABASE_URL', None)
    plan = [('default_release', ['scripts/run_release.py']+(['--local'] if local else []))]
    plan += [(name, ['-m', 'fmcg.'+name]) for name in ('promotion_scenario', 'receipt_scenario', 'q4_plan')]
    try:
        for name, arguments in plan:
            print('Running candidate stage: '+name, flush=True)
            completed = run([sys.executable, *arguments], cwd=root, env=env, capture_output=True, text=True)
            log = completed.stdout+completed.stderr
            for key in ('DATABASE_URL', 'FMCG_TEST_DATABASE_URL'):
                url = os.environ.get(key)
                if url:
                    log = log.replace(url, '[database URL]')
                    password = urlparse(url).password
                    if password: log = log.replace(password, '[redacted]')
            (output/('candidate_'+name+'.txt')).write_text(log)
            result['stages'].append(dict(name=name, returncode=completed.returncode,
                status='passed' if completed.returncode == 0 else 'failed'))
            if completed.returncode: raise ValueError('Stage failed: '+name)
            if name == 'default_release':
                release = json.loads((output/'release_status.json').read_text())
                expected = 'passed_local_database_pending' if local else 'passed'
                timestamp = dt.datetime.fromisoformat(release['started_utc'])
                if timestamp < start or release['status'] != expected:
                    raise ValueError('Default release evidence is stale or not accepted')
                if not local and release.get('database_verified') is not True:
                    raise ValueError('Database verification missing from default release')
                result['database_verified'] = False if local else True
                result['core_tests'] = release['tests']
        if any(not (output/path).is_file() or (output/path).stat().st_mtime < start.timestamp()
               for _, path in PAGES):
            raise ValueError('Missing or stale candidate dashboard')
        result['status'] = 'passed_local_database_pending' if local else 'passed'
        result['pages'] = [path for _, path in PAGES]
        links = ''.join('<li><a href="'+escape(path)+'">'+escape(label)+'</a></li>' for label,path in PAGES)
        entry.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>FMCG release candidate</title><style>body{font:18px system-ui;max-width:850px;margin:40px auto;padding:20px;color:#173045}li{margin:18px 0}</style>'
            '<h1>FMCG release candidate</h1><p>100% synthetic · '+escape(result['status'])+'</p>'
            '<p>Core database verification: '+str(result['database_verified']).lower()+'. Supplemental scenarios retain their own assumptions and evaluation cohorts.</p>'
            '<ul>'+links+'</ul><p><a href="candidate_status.json">Candidate status and stage evidence</a></p>'
            '<p>Receipt-risk results include lower recall and PR-AUC than the comparator. Q4 plans are authored assumptions and do not close the annual target. This build does not establish production readiness or real-data accuracy.</p></html>', encoding='utf-8')
    except (ValueError, OSError, KeyError, TypeError) as error:
        result.update(status='failed', reason=str(error) if isinstance(error,ValueError) else 'Missing or invalid process/file evidence')
    except KeyboardInterrupt:
        result.update(status='interrupted', reason='Candidate interrupted')
    finally:
        result['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        status_path.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='No database connections; database verification remains pending')
    result = execute(parser.parse_args().local)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] in ('passed', 'passed_local_database_pending') else 2)
