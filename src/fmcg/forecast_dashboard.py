"""Offline M3 dashboard, exact calculation outputs consumed as decimal strings."""
import argparse
import json
from pathlib import Path
from .generate import ROOT

def render(output):
    payload=json.loads((output/'forecast.json').read_text())
    embedded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')
    target=output/'dashboard.html'; target.write_text((ROOT/'dashboard/m3.html').read_text().replace('__FORECAST__',embedded),encoding='utf-8'); return target
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=ROOT/'output/m3'); a=p.parse_args(); print(render(a.output))
