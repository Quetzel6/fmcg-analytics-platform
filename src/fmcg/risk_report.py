"""DQ-gated M5 observed panels and separate evaluation outputs."""
import argparse
import json
from pathlib import Path
from .generate import ROOT
from .validate import validate
from .risk.metrics import build,summarize,load_policy
from .risk_validation import evaluate
from .promotion_report import write_csv,encode

def export(rows,metrics,loss,availability,policy,output):
    output.mkdir(parents=True,exist_ok=True);groups=summarize(rows);as_of=max(r['date'] for r in rows)
    latest=[r for r in rows if r['date']==as_of]
    for name,values in [('daily_inventory_risk',rows),('monthly_availability',groups),('latest_risk',latest),('risk_validation',metrics),('lost_sales_validation',loss),('availability_validation',availability)]:
        write_csv(output/(name+'.csv'),values)
    payload=dict(as_of=as_of,policy=policy,latest=latest,monthly=groups,risk_validation=metrics,lost_sales_validation=loss,availability_validation=availability)
    (output/'risk.json').write_text(json.dumps(encode(payload),indent=2)+'\n')
    (output/'protocol.json').write_text(json.dumps(policy,indent=2)+'\n');return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data');p.add_argument('--config',type=Path,default=ROOT/'config/scenario.toml');p.add_argument('--policy',type=Path,default=ROOT/'config/risk.toml');p.add_argument('--output',type=Path,default=ROOT/'output/m5');a=p.parse_args()
    policy=load_policy(a.policy);quality,_=validate(a.data,a.config)
    if quality['status']!='passed':raise SystemExit('DQ gate failed; no M5 exports written')
    rows=build(a.data,policy=policy);metrics,loss,availability=evaluate(a.data,rows,policy);export(rows,metrics,loss,availability,policy,a.output)
    print(f'PASS: {len(rows)} observed inventory rows; M5 exports and separate validation written')
