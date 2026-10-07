"""Isolated test batches with source-fingerprinted, complete result collection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

root=Path(__file__).resolve().parents[1]; output=root/'output/checks'; output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tests'))
environment=dict(os.environ); environment['PYTHONPATH']=os.pathsep.join([str(root/'src'),str(root/'tests')])

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite): yield from flatten(item)
        else: yield item.id()

def fingerprint():
    digest=hashlib.sha256()
    for folder in ('src','tests','sql','config'):
        for path in sorted((root/folder).rglob('*')):
            if path.is_file() and path.suffix in ('.py','.sql','.toml'):
                digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()

groups=[]
for pattern in ('test_m1.py','test_m2.py','test_m3.py','test_m4.py','test_m5.py'):
    ids=list(flatten(unittest.defaultTestLoader.discover(str(root/'tests'),pattern=pattern)))
    for first in range(0,len(ids),8): groups.append(ids[first:first+8])

p=argparse.ArgumentParser(); p.add_argument('--batch',type=int,help='Run one numbered batch'); p.add_argument('--collect',action='store_true',help='Collect matching completed batches'); args=p.parse_args(); source=fingerprint()
if not args.collect:
    selected=[args.batch] if args.batch else list(range(1,len(groups)+1))
    for number in selected:
        if not 1<=number<=len(groups): raise SystemExit('Unknown batch')
        path=output/f'batch_{number:02d}.txt'; print(f'Running batch {number}/{len(groups)}',flush=True)
        with path.open('w') as stream:
            process=subprocess.run([sys.executable,'-m','unittest',*groups[number-1],'-v'],cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
        text=path.read_text(); match=re.search(r'Ran (\d+) tests?',text); skip=re.search(r'OK \(skipped=(\d+)\)',text)
        okay=process.returncode==0 and match is not None and re.search(r'^OK(?: \(skipped=\d+\))?$',text,re.M) is not None
        skipped=int(skip.group(1)) if skip else 0; total=int(match.group(1)) if match else 0
        result=dict(batch=number,source_sha256=source,ids=groups[number-1],status='passed' if okay else 'failed',tests=total,passed=total-skipped,skipped=skipped)
        (output/f'batch_{number:02d}.json').write_text(json.dumps(result,indent=2)+'\n')
        if not okay: raise SystemExit(f'Failed/incomplete: {path}')
        print(f'Batch {number} passed ({skipped} skipped)',flush=True)
if args.collect or not args.batch:
    results=[]; logs=[]
    for number,ids in enumerate(groups,1):
        path=output/f'batch_{number:02d}.json'
        if not path.exists(): raise SystemExit(f'Batch {number} missing')
        result=json.loads(path.read_text())
        if result['source_sha256']!=source or result['status']!='passed' or result['ids']!=ids: raise SystemExit(f'Batch {number} stale or failed; rerun')
        results.append(result); logs.append(f'===== batch {number} =====\n'+(output/f'batch_{number:02d}.txt').read_text())
    summary=dict(status='passed',source_sha256=source,tests=sum(r['tests'] for r in results),passed=sum(r['passed'] for r in results),skipped=sum(r['skipped'] for r in results),batches=len(groups))
    (root/'output/all_test_results.txt').write_text('\n'.join(logs)); (root/'output/test_summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
