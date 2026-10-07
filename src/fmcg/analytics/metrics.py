"""M2: C01-C10 and S01-S07, exact integer/rational arithmetic."""
import calendar
import csv
import datetime as dt
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


def read(root,name):
    with (root/'warehouse'/f'{name}.csv').open(newline='',encoding='utf-8') as stream: return list(csv.DictReader(stream))

def ratio(n,d,percent=False):
    return Fraction(n*(100 if percent else 1),d) if d else None

def decimal_text(value):
    if value is None: return None
    if isinstance(value,Fraction):
        with localcontext() as context:
            context.prec=50
            return str(Decimal(value.numerator)/Decimal(value.denominator))
    return str(value)

def effects(ly_amount,ly_qty,ty_amount,ty_qty):
    delta=ty_amount-ly_amount
    if not ly_qty or not ty_qty: return dict(volume_effect_satang=None,price_effect_satang=None,undecomposed_delta_satang=delta)
    volume=Fraction((ty_qty-ly_qty)*ly_amount,ly_qty)
    price=Fraction(delta)-volume
    return dict(volume_effect_satang=volume,price_effect_satang=price,undecomposed_delta_satang=0)

def percentile(values,p=Fraction(9,10)):
    if not values: return None
    values=sorted(values); index=(len(values)-1)*p; lower=index.numerator//index.denominator; upper=min(lower+1,len(values)-1)
    return Fraction(values[lower])+(values[upper]-values[lower])*(index-lower)

def service(lines,as_of):
    cohort=[r for r in lines if r['order_date']<=as_of]
    due=[r for r in cohort if r['promised_date']<=as_of]
    def delivered(r): return r['delivered_qty'] if r['delivered_date'] and r['delivered_date']<=as_of else 0
    def ontime(r): return bool(r['delivered_date'] and r['delivered_date']<=min(as_of,r['promised_date']))
    def full(r): return delivered(r)==r['ordered_qty']
    groups=defaultdict(list)
    for r in due: groups[r['order_id']].append(r)
    ordered=sum(r['ordered_qty'] for r in due); shipped=sum(delivered(r) for r in due)
    leads=[(r['delivered_date']-r['order_date']).days for r in cohort if r['delivered_date'] and r['delivered_date']<=as_of]
    # Positive short deliveries close the line; the remainder is cancelled.
    opened=[r for r in cohort if not r['delivered_date'] or r['delivered_date']>as_of]
    return dict(due_lines=len(due),due_orders=len(groups),pending_lines=len(cohort)-len(due),ordered_due_qty=ordered,delivered_due_qty=shipped,fill_rate_pct=ratio(shipped,ordered,True),on_time_rate_pct=ratio(sum(ontime(r) for r in due),len(due),True),in_full_rate_pct=ratio(sum(full(r) for r in due),len(due),True),line_otif_pct=ratio(sum(ontime(r) and full(r) for r in due),len(due),True),order_otif_pct=ratio(sum(all(ontime(r) and full(r) for r in group) for group in groups.values()),len(groups),True),mean_lead_days=ratio(sum(leads),len(leads)),p90_lead_days=percentile(leads),backlog_qty=sum(r['ordered_qty'] for r in opened),overdue_backlog_qty=sum(r['ordered_qty'] for r in opened if r['promised_date']<=as_of))

def build(root,as_of):
    metadata=json.loads((root/'manifest.json').read_text())
    if as_of.day!=calendar.monthrange(as_of.year,as_of.month)[1]: raise ValueError('M2 comparisons require month-end as-of')
    if not dt.date.fromisoformat(metadata['start_date'])<=as_of<=dt.date.fromisoformat(metadata['as_of_date']): raise ValueError('As-of outside observed period')
    customers=read(root,'dim_customer'); products=read(root,'dim_product'); stores={r['store_id']:r for r in read(root,'dim_store')}
    totals=defaultdict(lambda:[0,0]); orders=[]
    for row in read(root,'fact_sales_daily'):
        day=dt.date.fromisoformat(row['date'])
        if day>as_of: continue
        key=(day.year,day.month,stores[row['store_id']]['customer_id'],row['product_id'],'SO')
        totals[key][0]+=int(row['amount_satang']); totals[key][1]+=int(row['quantity'])
    for row in read(root,'fact_order_line'):
        r=dict(row)
        for k in ('order_date','promised_date','delivered_date'): r[k]=dt.date.fromisoformat(r[k]) if r[k] else None
        for k in ('ordered_qty','delivered_qty','amount_satang'): r[k]=int(r[k])
        orders.append(r)
        day=r['delivered_date']
        if day and day<=as_of:
            key=(day.year,day.month,stores[r['store_id']]['customer_id'],r['product_id'],'SI')
            totals[key][0]+=r['amount_satang']; totals[key][1]+=r['delivered_qty']
    start=dt.date.fromisoformat(json.loads((root/'manifest.json').read_text())['start_date'])
    monthly=[]
    for year in range(start.year,as_of.year+1):
        for month in range(1,13 if year<as_of.year else as_of.month+1):
            for c in customers:
                for p in products:
                    for kind in ('SI','SO'):
                        amount,qty=totals[year,month,c['customer_id'],p['product_id'],kind]
                        previous=(year,month-1) if month>1 else (year-1,12)
                        previous_available=previous>=(start.year,start.month)
                        prior_amount,prior_qty=totals[previous[0],previous[1],c['customer_id'],p['product_id'],kind]
                        ly_available=year-1>=start.year
                        ly_amount,ly_qty=totals[year-1,month,c['customer_id'],p['product_id'],kind]
                        monthly.append(dict(year=year,month=month,customer_id=c['customer_id'],customer_name=c['customer_name'],product_id=p['product_id'],product_name=p['product_name'],brand=p['brand'],category=p['category'],sales_type=kind,amount_satang=amount,quantity=qty,asp_satang=ratio(amount,qty),yoy_amount_pct=ratio(amount-ly_amount,ly_amount,True) if ly_available else None,yoy_qty_pct=ratio(qty-ly_qty,ly_qty,True) if ly_available else None,mom_amount_pct=ratio(amount-prior_amount,prior_amount,True) if previous_available else None,mom_qty_pct=ratio(qty-prior_qty,prior_qty,True) if previous_available else None))
    sku=[]
    for c in customers:
        for kind in ('SI','SO'):
            partition=[]
            for p in products:
                def ytd(year,index): return sum(totals[year,m,c['customer_id'],p['product_id'],kind][index] for m in range(1,as_of.month+1))
                la,lq,ta,tq=ytd(as_of.year-1,0),ytd(as_of.year-1,1),ytd(as_of.year,0),ytd(as_of.year,1)
                row=dict(customer_id=c['customer_id'],customer_name=c['customer_name'],product_id=p['product_id'],product_name=p['product_name'],brand=p['brand'],category=p['category'],sales_type=kind,ly_amount_satang=la,ty_amount_satang=ta,ly_qty=lq,ty_qty=tq,yoy_amount_pct=ratio(ta-la,la,True),yoy_qty_pct=ratio(tq-lq,lq,True),ly_asp_satang=ratio(la,lq),ty_asp_satang=ratio(ta,tq))
                if kind=='SO': row.update(effects(la,lq,ta,tq))
                partition.append(row)
            denominator=sum(r['ty_amount_satang'] for r in partition); ranks={value:i+1 for i,value in enumerate(sorted({r['ty_amount_satang'] for r in partition},reverse=True))}
            for r in partition: r.update(contribution_pct=ratio(r['ty_amount_satang'],denominator,True),sku_rank=ranks[r['ty_amount_satang']])
            sku.extend(partition)
    categories=sorted({p['category'] for p in products}); targets=read(root,'fact_target_monthly'); category_ytd=[]; quarterly=[]
    for c in customers:
        for kind in ('SI','SO'):
            for cat in categories:
                rows=[r for r in sku if r['customer_id']==c['customer_id'] and r['sales_type']==kind and r['category']==cat]
                la=sum(r['ly_amount_satang'] for r in rows); ta=sum(r['ty_amount_satang'] for r in rows); lq=sum(r['ly_qty'] for r in rows); tq=sum(r['ty_qty'] for r in rows)
                row=dict(customer_id=c['customer_id'],customer_name=c['customer_name'],category=cat,sales_type=kind,ly_amount_satang=la,ty_amount_satang=ta,ly_qty=lq,ty_qty=tq,yoy_amount_pct=ratio(ta-la,la,True),yoy_qty_pct=ratio(tq-lq,lq,True),ty_asp_satang=ratio(ta,tq))
                if kind=='SI':
                    target=sum(int(t['target_amount_satang']) for t in targets if t['customer_id']==c['customer_id'] and t['category']==cat and dt.date.fromisoformat(t['month_start']).year==as_of.year and dt.date.fromisoformat(t['month_start']).month<=as_of.month)
                    row.update(ytd_target_satang=target,target_attainment_pct=ratio(ta,target,True))
                category_ytd.append(row)
                for quarter in range(1,(as_of.month-1)//3+2):
                    months=range((quarter-1)*3+1,min(quarter*3,as_of.month)+1)
                    pids=[p['product_id'] for p in products if p['category']==cat]
                    def qtotal(year,index): return sum(totals[year,m,c['customer_id'],pid,kind][index] for m in months for pid in pids)
                    qa,qla,qq,qlq=qtotal(as_of.year,0),qtotal(as_of.year-1,0),qtotal(as_of.year,1),qtotal(as_of.year-1,1)
                    quarterly.append(dict(customer_id=c['customer_id'],customer_name=c['customer_name'],category=cat,sales_type=kind,quarter=quarter,months=list(months),ty_amount_satang=qa,ly_amount_satang=qla,ty_qty=qq,ly_qty=qlq,yoy_amount_pct=ratio(qa-qla,qla,True),yoy_qty_pct=ratio(qq-qlq,qlq,True)))
    service_rows=[]
    service_rows.append(dict(customer_id='ALL',customer_name='All retailers',**service(orders,as_of)))
    for c in customers: service_rows.append(dict(customer_id=c['customer_id'],customer_name=c['customer_name'],**service([r for r in orders if stores[r['store_id']]['customer_id']==c['customer_id']],as_of)))
    return dict(data_class='100% SYNTHETIC',as_of=as_of.isoformat(),period=f'Jan–{as_of.month:02d} {as_of.year} vs {as_of.year-1}',definitions='docs/KPI_DICTIONARY.md',implemented_ids=['C01','C02','C03','C04','C05','C06','C07','C08','C09','C10','S01','S02','S03','S04','S05','S06','S07'],monthly=monthly,sku_ytd=sku,category_ytd=category_ytd,quarterly=quarterly,service=service_rows)

def encode(value):
    if isinstance(value,bool): return value
    if isinstance(value,Fraction): return decimal_text(value)
    if isinstance(value,int): return str(value)  # Prevent JavaScript precision loss, including large money totals.
    if isinstance(value,list): return [encode(v) for v in value]
    if isinstance(value,dict): return {k:encode(v) for k,v in value.items()}
    return value

def export(report,output):
    output.mkdir(parents=True,exist_ok=True)
    for name in ('monthly','sku_ytd','category_ytd','quarterly','service'):
        rows=report[name]; fields=list(dict.fromkeys(k for r in rows for k in r))
        with (output/f'{name}.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n'); writer.writeheader()
            writer.writerows({k:decimal_text(v) if isinstance(v,Fraction) else v for k,v in r.items()} for r in rows)
    # Canonical rational evidence keeps repeating-price decomposition exact.
    evidence=[dict(customer_id=r['customer_id'],product_id=r['product_id'],**{k:dict(numerator=str(v.numerator),denominator=str(v.denominator)) for k,v in r.items() if k in ('volume_effect_satang','price_effect_satang') and isinstance(v,Fraction)}) for r in report['sku_ytd'] if r['sales_type']=='SO']
    rational_evidence={name:[{field:dict(numerator=str(v.numerator),denominator=str(v.denominator)) for field,v in row.items() if isinstance(v,Fraction)} for row in report[name]] for name in ('monthly','sku_ytd','category_ytd','quarterly','service')}
    (output/'rational_exact.json').write_text(json.dumps(rational_evidence,indent=2)+'\n')
    (output/'price_volume_exact.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (output/'analytics.json').write_text(json.dumps(encode(report),indent=2,ensure_ascii=False)+'\n')
