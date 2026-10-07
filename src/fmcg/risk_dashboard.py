"""Offline inventory/risk dashboard."""
import argparse
from pathlib import Path
from .generate import ROOT
from .promotion_dashboard import render

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'output/m5/risk.json');p.add_argument('--output',type=Path,default=ROOT/'output/m5/dashboard.html');a=p.parse_args()
    render(a.input,ROOT/'dashboard/m5.html',a.output);print('PASS: offline M5 dashboard rendered')
