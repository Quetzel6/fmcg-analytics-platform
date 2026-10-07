"""QA orchestration outside the analytics package."""
import argparse
import datetime as dt
import json
from pathlib import Path
from .generate import ROOT
from .validate import validate
from .analytics.metrics import build,export

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,default=ROOT/'data'); p.add_argument('--config',type=Path,default=ROOT/'config/scenario.toml'); p.add_argument('--output',type=Path,default=ROOT/'output/m2'); a=p.parse_args()
    quality,_=validate(a.data,a.config)
    if quality['status']!='passed': raise SystemExit('DQ gate failed; no M2 export written')
    end=dt.date.fromisoformat(json.loads((a.data/'manifest.json').read_text())['as_of_date'])
    report=build(a.data,end); export(report,a.output); print('PASS: M2 commercial/service reports exported')
