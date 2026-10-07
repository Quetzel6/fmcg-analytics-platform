"""DQ-gated M4 observed estimates and separate validation exports."""
import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path
from .generate import ROOT
from .validate import validate
from .analytics.metrics import decimal_text
from .uplift.estimators import build,summarize
from .promotion_validation import evaluate

def encode(value):
    if isinstance(value,Fraction): return decimal_text(value)
    if isinstance(value,dict): return {k:encode(v) for k,v in value.items()}
    if isinstance(value,list): return [encode(v) for v in value]
    return value

def write_csv(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(encode(rows))

def export(rows,validation_rows,validation_summary,output):
    output.mkdir(parents=True,exist_ok=True)
    groups=summarize(rows)
    for name,values in [('promotion_estimates',rows),('retailer_category_summary',groups),('validation_errors',validation_rows),('validation_summary',validation_summary)]:
        write_csv(output/(name+'.csv'),values)
    payload=dict(estimates=rows,groups=groups,validation=validation_summary)
    (output/'promotion.json').write_text(json.dumps(encode(payload),indent=2)+'\n')
    exact={}
    for index,row in enumerate(rows):
        for key,value in row.items():
            if isinstance(value,Fraction): exact[f'{index}.{key}']={'numerator':str(value.numerator),'denominator':str(value.denominator)}
    (output/'rational_exact.json').write_text(json.dumps(exact,indent=2)+'\n')
    return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data');p.add_argument('--config',type=Path,default=ROOT/'config/scenario.toml');p.add_argument('--output',type=Path,default=ROOT/'output/m4');a=p.parse_args()
    quality,_=validate(a.data,a.config)
    if quality['status']!='passed': raise SystemExit('DQ gate failed; no M4 exports written')
    rows=build(a.data); errors,summary=evaluate(a.data,rows);export(rows,errors,summary,a.output)
    print(f'PASS: {len(rows)} estimator rows; {sum(r["status"]=="available" for r in rows)} available')
