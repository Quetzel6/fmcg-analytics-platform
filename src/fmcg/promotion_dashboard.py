"""Render offline M4 dashboard with data-safe script embedding."""
import argparse
from pathlib import Path
from .generate import ROOT

def render(source,template,target):
    payload=source.read_text().replace('<','\\u003c')
    target.write_text(template.read_text().replace('__M4_DATA__',payload),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'output/m4/promotion.json');p.add_argument('--output',type=Path,default=ROOT/'output/m4/dashboard.html');a=p.parse_args()
    render(a.input,ROOT/'dashboard/m4.html',a.output);print('PASS: offline M4 dashboard rendered')
