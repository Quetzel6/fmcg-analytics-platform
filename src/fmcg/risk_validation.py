"""Validation-only future labels and latent lost-demand comparisons."""
import csv
import datetime as dt
from collections import defaultdict
from fractions import Fraction
from .analytics.metrics import ratio

DAY=dt.timedelta(days=1)

def binary_metrics(scored):
    """Group tied scores; AP is step-integral and PR-AUC is trapezoidal."""
    n=len(scored); positives=sum(label for score,flag,label in scored)
    tp=sum(flag and label for score,flag,label in scored);fp=sum(flag and not label for score,flag,label in scored);fn=positives-tp
    base=dict(samples=n,positives=positives,prevalence_pct=ratio(positives,n,True),tp=tp,fp=fp,fn=fn,tn=n-tp-fp-fn,
        precision=ratio(tp,tp+fp),recall=ratio(tp,positives),average_precision=None,pr_auc=None)
    if not positives:return base
    buckets=defaultdict(list)
    for score,flag,label in scored:buckets[score].append(label)
    seen=correct=0;prev_recall=Fraction(0);prev_precision=Fraction(1);ap=auc=Fraction(0)
    for score,labels in sorted(buckets.items(),reverse=True):
        seen+=len(labels);correct+=sum(labels);recall=Fraction(correct,positives);precision=Fraction(correct,seen)
        ap+=(recall-prev_recall)*precision;auc+=(recall-prev_recall)*(precision+prev_precision)/2
        prev_recall,prev_precision=recall,precision
    base.update(average_precision=ap,pr_auc=auc);return base

def evaluate(root,rows,policy):
    with (root/'truth/truth_demand_daily.csv').open(newline='') as stream:
        demand={(r['date'],r['store_id'],r['product_id']):int(r['lost_qty']) for r in csv.DictReader(stream)}
    by_key={(r['date'],r['store_id'],r['product_id']):r for r in rows};labels=[]
    for row in rows:
        day=dt.date.fromisoformat(row['date']);sid,pid=row['store_id'],row['product_id']
        future=[(str(day+i*DAY),sid,pid) for i in range(1,8)]
        if not row['history_complete'] or not all(k in by_key and k in demand for k in future):continue
        labels.append(dict(row,label=any(demand[k]>0 for k in future)))
    metrics=[]
    for cohort in ('all_eligible','heldout_2026'):
        group=[r for r in labels if cohort=='all_eligible' or r['date']>=policy['heldout_start']]
        for method,score_key,flag_key in [('weekday_uncensored_cover','risk_score','risk_flag'),('naive_cover_7','naive_score','naive_flag')]:
            scored=[(r[score_key],r[flag_key],r['label']) for r in group if r[score_key] is not None]
            metrics.append(dict(cohort=cohort,method=method,eligible_days=len(group),unscored_days=len(group)-len(scored),**binary_metrics(scored)))
        common=[r for r in group if r['risk_score'] is not None and r['naive_score'] is not None]
        for method,score_key,flag_key in [('weekday_uncensored_cover','risk_score','risk_flag'),('naive_cover_7','naive_score','naive_flag')]:
            metrics.append(dict(cohort=cohort+'_matched',method=method,eligible_days=len(group),unscored_days=len(group)-len(common),**binary_metrics([(r[score_key],r[flag_key],r['label']) for r in common])))
    monthly=defaultdict(list);availability=defaultdict(list)
    for row in rows:
        key=(row['date'],row['store_id'],row['product_id'])
        if key not in demand:raise ValueError('Missing validation demand key')
        actual=demand[key]; group=(row['date'][:7],row['customer_id'],row['category'])
        availability[group].append((row['observed_stockout'],actual>0))
        monthly[group].append((row['estimated_lost_units'],actual))
    loss_rows=[];availability_rows=[]
    for (month,cid,category),group in sorted(monthly.items()):
        matched=[(estimate,actual) for estimate,actual in group if estimate is not None]
        estimated=sum((e for e,a in matched),Fraction());actual=sum(a for e,a in matched);error=estimated-actual
        loss_rows.append(dict(month=month,customer_id=cid,category=category,total_days=len(group),estimated_days=len(matched),unestimated_days=len(group)-len(matched),
            estimated_lost_units=estimated,matched_actual_lost_units=actual,all_actual_lost_units=sum(a for e,a in group),
            aggregate_error_units=error,absolute_aggregate_error_units=abs(error),
            daily_mae_units=sum((abs(e-a) for e,a in matched),Fraction())/len(matched) if matched else None,
            daily_wape_pct=ratio(sum((abs(e-a) for e,a in matched),Fraction()),actual,True)))
        pairs=availability[month,cid,category];observed=sum(o for o,a in pairs);actual_oos=sum(a for o,a in pairs)
        availability_rows.append(dict(month=month,customer_id=cid,category=category,store_sku_days=len(pairs),observed_stockout_days=observed,actual_lost_demand_days=actual_oos,
            observed_availability_pct=ratio(len(pairs)-observed,len(pairs),True),actual_availability_pct=ratio(len(pairs)-actual_oos,len(pairs),True),
            proxy_tp=sum(o and a for o,a in pairs),proxy_fp=sum(o and not a for o,a in pairs),proxy_fn=sum(not o and a for o,a in pairs)))
    return metrics,loss_rows,availability_rows
