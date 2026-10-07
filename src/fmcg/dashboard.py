"""Standalone M2 presentation, no external scripts or server required."""
import argparse
import json
from pathlib import Path
from .generate import ROOT

def render(output):
    payload=json.loads((output/'analytics.json').read_text())
    embedded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c')
    html=(ROOT/'dashboard/m2.html').read_text().replace('__REPORT__',embedded)
    path=output/'dashboard.html'; path.write_text(html,encoding='utf-8'); return path
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=ROOT/'output/m2'); a=p.parse_args(); print(render(a.output))
