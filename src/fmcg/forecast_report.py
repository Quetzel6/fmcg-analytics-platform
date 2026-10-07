"""Validation gate before M3 forecast exports."""
import argparse
from pathlib import Path
from .generate import ROOT
from .validate import validate
from .forecast.baselines import build,export
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,default=ROOT/'data'); p.add_argument('--config',type=Path,default=ROOT/'config/scenario.toml'); p.add_argument('--output',type=Path,default=ROOT/'output/m3'); a=p.parse_args()
    quality,_=validate(a.data,a.config)
    if quality['status']!='passed': raise SystemExit('DQ gate failed; no M3 export written')
    result=build(a.data); export(result,a.output); print('PASS: M3 backtests and Q4 outlook exported; selected '+result['selection']['selected_method'])
