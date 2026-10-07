"""F01-F04 and C11-C12. Integer money and rational forecasts; no external drivers."""
import calendar
import csv
import datetime as dt
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from ..analytics.metrics import read,encode,decimal_text

METHODS=('seasonal_naive','ly_ytd_growth','seasonal_run_rate')
ORIGINS=(dt.date(2025,9,30),dt.date(2026,6,30))

@dataclass
class Series:
    amounts: dict
    customers: list
    categories: list
    start: dt.date
    end: dt.date


def month_range(start,end):
    year,month=start.year,start.month
    while (year,month)<=(end.year,end.month):
        yield year,month
        year,month=(year+1,1) if month==12 else (year,month+1)


def load_series(root):
    metadata=json.loads((root/'manifest.json').read_text())
    start=dt.date.fromisoformat(metadata['start_date']); end=dt.date.fromisoformat(metadata['as_of_date'])
    customers=read(root,'dim_customer'); products={r['product_id']:r for r in read(root,'dim_product')}; stores={r['store_id']:r for r in read(root,'dim_store')}; categories=sorted({p['category'] for p in products.values()})
    amounts={(y,m,c['customer_id'],cat):0 for y,m in month_range(start,end) for c in customers for cat in categories}
    for r in read(root,'fact_order_line'):
        if not r['delivered_date']: continue
        date=dt.date.fromisoformat(r['delivered_date'])
        if not start<=date<=end: raise ValueError('Delivery outside observed period')
        key=date.year,date.month,stores[r['store_id']]['customer_id'],products[r['product_id']]['category']
        amounts[key]+=int(r['amount_satang'])
    return Series(amounts,customers,categories,start,end)


def train_at(series,origin):
    if origin.day!=calendar.monthrange(origin.year,origin.month)[1]: raise ValueError('Origin must be month end')
    if not series.start<=origin<=series.end: raise ValueError('Origin outside observed coverage')
    return {key:value for key,value in series.amounts.items() if key[:2]<=(origin.year,origin.month)}


def next_months(origin,horizon=3):
    months=[]; year,month=origin.year,origin.month
    for _ in range(horizon):
        year,month=(year+1,1) if month==12 else (year,month+1); months.append((year,month))
    return months


def predict(series,origin,method,horizon=3):
    if method not in METHODS: raise ValueError('Unknown baseline')
    if horizon!=3: raise ValueError('M3 evaluates a three-month horizon')
    history=train_at(series,origin); output=[]
    for customer in series.customers:
        cid=customer['customer_id']
        for category in series.categories:
            def get(y,m): return history.get((y,m,cid,category))
            factor=None; run_rate=None; indices={}; failure=None
            if method=='ly_ytd_growth':
                current=[get(origin.year,m) for m in range(1,origin.month+1)]; prior=[get(origin.year-1,m) for m in range(1,origin.month+1)]
                if any(v is None for v in current+prior): failure='missing_ytd_history'
                elif sum(prior)==0: failure='zero_ly_ytd'
                else: factor=Fraction(sum(current),sum(prior))
            elif method=='seasonal_run_rate':
                annual=[get(origin.year-1,m) for m in range(1,13)]
                trailing=[]
                y,m=origin.year,origin.month
                for _ in range(3): trailing.append((y,m)); y,m=(y-1,12) if m==1 else (y,m-1)
                if any(v is None for v in annual): failure='missing_prior_full_year'
                elif sum(annual)==0: failure='zero_prior_full_year'
                else:
                    average=Fraction(sum(annual),12); indices={m:Fraction(annual[m-1],1)/average for m in range(1,13)}
                    actual=[get(y,m) for y,m in trailing]
                    if any(v is None for v in actual): failure='missing_trailing_history'
                    elif any(indices[m]==0 for y,m in trailing): failure='zero_trailing_seasonal_index'
                    else: run_rate=sum(Fraction(value)/indices[m] for value,(y,m) in zip(actual,trailing))/3
            for year,month in next_months(origin,horizon):
                prediction=None; reason=failure
                if method=='seasonal_naive' or method=='ly_ytd_growth':
                    base=get(year-1,month)
                    if base is None: reason=reason or 'missing_ly_month'
                    elif not reason: prediction=Fraction(base)*(factor if method=='ly_ytd_growth' else 1)
                elif not reason: prediction=run_rate*indices[month]
                output.append(dict(origin=origin.isoformat(),year=year,month=month,customer_id=cid,customer_name=customer['customer_name'],category=category,method=method,forecast_satang=prediction,status='available' if prediction is not None else reason,growth_factor=factor if method=='ly_ytd_growth' else None))
    return output


def score(predictions,series):
    rows=[]; missing=0
    for p in predictions:
        row=dict(p); actual=series.amounts.get((p['year'],p['month'],p['customer_id'],p['category']))
        if actual is None: raise ValueError('Evaluation actual outside observed coverage')
        forecast=p['forecast_satang']; missing+=forecast is None
        row.update(actual_satang=actual,error_satang=forecast-actual if forecast is not None else None,absolute_error_satang=abs(forecast-actual) if forecast is not None else None); rows.append(row)
    total=sum(r['actual_satang'] for r in rows)
    complete=missing==0 and total!=0
    wape=sum(r['absolute_error_satang'] for r in rows)/total if complete else None
    bias=sum(r['error_satang'] for r in rows)/total if complete else None
    return rows,dict(method=predictions[0]['method'],origin=predictions[0]['origin'],points=len(rows),missing_predictions=missing,actual_total_satang=total,wape=wape,bias=bias,status='complete' if complete else ('incomplete_predictions' if missing else 'zero_actual_denominator'))


def select_method(scores):
    by={(r['origin'],r['method']):r for r in scores}; origins=[o.isoformat() for o in ORIGINS]; eligible=[]; decisions=[]
    for method in METHODS[1:]:
        comparisons=[]
        for origin in origins:
            baseline=by[origin,'seasonal_naive']['wape']; candidate=by[origin,method]['wape']
            comparisons.append(baseline is not None and candidate is not None and candidate<baseline)
        wins=all(comparisons); decisions.append(dict(method=method,beats_naive_at_both_origins=wins))
        if wins: eligible.append(method)
    chosen=min(eligible,key=lambda method:(sum(by[o,method]['wape'] for o in origins)/len(origins),METHODS.index(method))) if eligible else 'seasonal_naive'
    return dict(selected_method=chosen,rule='Strictly beat seasonal naive WAPE at both fixed origins; then lowest mean WAPE, deterministic method order for ties. Otherwise retain seasonal naive.',comparisons=decisions,selection_scope='Two synthetic historical backtests; no claim about future or real-data accuracy')


def build(root):
    series=load_series(root)
    if series.end!=dt.date(2026,9,30): raise ValueError('This M3 protocol requires as-of 2026-09-30 and a Q4 closing horizon')
    points=[]; scores=[]
    for origin in ORIGINS:
        for method in METHODS:
            predictions=predict(series,origin,method); rows,metrics=score(predictions,series)
            if metrics['points']!=36: raise ValueError('Expected 36 retailer-category-month points per origin/method')
            points.extend(rows); scores.append(metrics)
    selection=select_method(scores); forecasts=[]
    for method in METHODS: forecasts.extend(predict(series,series.end,method))
    selected=[r for r in forecasts if r['method']==selection['selected_method']]; targets=read(root,'fact_target_monthly'); outlook=[]
    for customer in series.customers:
        cid=customer['customer_id']
        for category in series.categories:
            actual=sum(series.amounts[series.end.year,m,cid,category] for m in range(1,series.end.month+1))
            annual_target=sum(int(t['target_amount_satang']) for t in targets if t['customer_id']==cid and t['category']==category and dt.date.fromisoformat(t['month_start']).year==series.end.year)
            rows=[r for r in selected if r['customer_id']==cid and r['category']==category]
            remaining=sum(r['forecast_satang'] for r in rows) if all(r['forecast_satang'] is not None for r in rows) else None
            full=actual+remaining if remaining is not None else None
            outlook.append(dict(customer_id=cid,customer_name=customer['customer_name'],category=category,selected_method=selection['selected_method'],actual_ytd_satang=actual,forecast_remaining_satang=remaining,annual_target_satang=annual_target,full_year_outlook_satang=full,gap_to_annual_target_satang=annual_target-full if full is not None else None,status='planning_estimate' if full is not None else 'unavailable_forecast'))
    summaries=[]
    for cid,name in [('ALL','All retailers')]+[(c['customer_id'],c['customer_name']) for c in series.customers]:
        rows=[r for r in outlook if cid=='ALL' or r['customer_id']==cid]
        summary=dict(customer_id=cid,customer_name=name,selected_method=selection['selected_method'])
        for field in ('actual_ytd_satang','forecast_remaining_satang','annual_target_satang','full_year_outlook_satang','gap_to_annual_target_satang'):
            summary[field]=sum(r[field] for r in rows) if all(r[field] is not None for r in rows) else None
        summaries.append(summary)
    return dict(data_class='100% SYNTHETIC',as_of=series.end.isoformat(),forecast_object='Sale-In amount recognised on delivered_date; customer x category x month',definitions='docs/KPI_DICTIONARY.md',source_manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),backtest_points=points,backtest_scores=scores,selection=selection,forecasts=forecasts,outlook=outlook,outlook_summary=summaries)


def export(report,output):
    output.mkdir(parents=True,exist_ok=True)
    for name in ('backtest_points','backtest_scores','forecasts','outlook','outlook_summary'):
        rows=report[name]; fields=list(dict.fromkeys(k for r in rows for k in r))
        with (output/f'{name}.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n'); writer.writeheader(); writer.writerows({k:decimal_text(v) if isinstance(v,Fraction) else v for k,v in r.items()} for r in rows)
    (output/'forecast.json').write_text(json.dumps(encode(report),indent=2,ensure_ascii=False)+'\n')
    exact={name:[{field:dict(numerator=str(value.numerator),denominator=str(value.denominator)) for field,value in row.items() if isinstance(value,Fraction)} for row in report[name]] for name in ('backtest_points','backtest_scores','forecasts','outlook','outlook_summary')}
    (output/'rational_exact.json').write_text(json.dumps(exact,indent=2)+'\n')
