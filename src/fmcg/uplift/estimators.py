"""Observed Sell-Out estimators. No private latent demand inputs."""
import datetime as dt
from collections import defaultdict
from fractions import Fraction
from ..analytics.metrics import read, ratio

DAY=dt.timedelta(days=1)
def dates(start,end):
    return [start+dt.timedelta(days=i) for i in range((end-start).days+1)]

def weekday_means(series,window):
    groups=defaultdict(list)
    for day in window:
        if day not in series: return None
        groups[day.weekday()].append(series[day])
    if len(groups)!=7: return None
    return {key:Fraction(sum(values),len(values)) for key,values in groups.items()}

def estimate(series,pre,promo,post,controls=(),method='B1'):
    means=weekday_means(series,pre)
    if means is None or any(day not in series for day in promo+post):
        return {'status':'unavailable','reason':'incomplete_window'}
    baselines={day:means[day.weekday()] for day in promo+post}
    if method=='B2':
        if not controls: return {'status':'unavailable','reason':'no_clean_control'}
        pooled={day:sum(control[day] for control in controls) for day in pre+promo+post}
        control_means=weekday_means(pooled,pre)
        # Additive DiD after scaling control units to the treated pre-period level.
        control_pre=sum(pooled[day] for day in pre)
        if not control_pre: return {'status':'unavailable','reason':'zero_control_baseline'}
        scale=Fraction(sum(series[day] for day in pre),control_pre)
        baselines={day:baselines[day]+scale*(pooled[day]-control_means[day.weekday()]) for day in promo+post}
        if any(value<0 for value in baselines.values()):
            return {'status':'unavailable','reason':'negative_daily_baseline'}
    baseline=sum(baselines[day] for day in promo); post_base=sum(baselines[day] for day in post)
    if not baseline or not post_base: return {'status':'unavailable','reason':'zero_treated_baseline'}
    actual=sum(series[day] for day in promo); post_actual=sum(series[day] for day in post)
    incremental=actual-baseline; post_incremental=post_actual-post_base
    return dict(status='available',reason='',baseline_units=baseline,actual_units=actual,
        incremental_units=incremental,uplift_pct=ratio(incremental,baseline,True),
        post_baseline_units=post_base,post_actual_units=post_actual,post_incremental_units=post_incremental,
        post_dip_pct=ratio(post_incremental,post_base,True),net_uplift_pct=ratio(incremental+post_incremental,baseline,True))

def build(root,as_of=dt.date(2026,9,30)):
    stores={row['store_id']:row['customer_id'] for row in read(root,'dim_store')}
    products={row['product_id']:row['category'] for row in read(root,'dim_product')}
    customers=sorted(set(stores.values())); series=defaultdict(lambda:defaultdict(int)); stockouts=set()
    for row in read(root,'fact_sales_daily'):
        day=dt.date.fromisoformat(row['date'])
        if day<=as_of: series[stores[row['store_id']],row['product_id']][day]+=int(row['quantity'])
    for row in read(root,'fact_inventory_daily'):
        day=dt.date.fromisoformat(row['date'])
        if day<=as_of and int(row['closing_qty'])==0: stockouts.add((stores[row['store_id']],row['product_id'],day))
    promotions=[]
    for row in read(root,'dim_promotion'):
        promotions.append(dict(row,start=dt.date.fromisoformat(row['start_date']),end=dt.date.fromisoformat(row['end_date'])))
    output=[]
    for row in promotions:
        start,end=row['start'],row['end']; pre=dates(start-28*DAY,start-DAY); promo=dates(start,end); post=dates(end+DAY,end+14*DAY)
        cid,pid=row['customer_id'],row['product_id']; eligible=[]
        for other in customers:
            if other==cid: continue
            contaminated=any(p['customer_id']==other and p['product_id']==pid and p['start']<=post[-1] and p['end']+14*DAY>=pre[0] for p in promotions)
            if not contaminated and all(day in series[other,pid] for day in pre+promo+post): eligible.append(other)
        own_contaminated=any(p['promo_id']!=row['promo_id'] and p['customer_id']==cid and p['product_id']==pid and p['start']<=post[-1] and p['end']+14*DAY>=pre[0] for p in promotions)
        for method in ('B1','B2'):
            result=estimate(series[cid,pid],pre,promo,post,[series[other,pid] for other in eligible],method)
            if own_contaminated: result=dict(status='unavailable',reason='treated_window_contaminated')
            output.append(dict(promo_id=row['promo_id'],customer_id=cid,category=products[pid],product_id=pid,
                start_date=str(start),end_date=str(end),method=method,control_customer_ids=','.join(eligible) if method=='B2' else '',
                censored=any((cid,pid,day) in stockouts for day in promo),
                post_censored=any((cid,pid,day) in stockouts for day in post),**result))
    return output

def summarize(rows):
    result=[]
    keys=sorted(set((r['method'],r['customer_id'],r['category']) for r in rows))
    for method,cid,category in keys:
        group=[r for r in rows if (r['method'],r['customer_id'],r['category'])==(method,cid,category)]
        for cohort in ('all','uncensored'):
            selected=[r for r in group if cohort=='all' or not r['censored']]
            valid=[r for r in selected if r['status']=='available']
            baseline=sum(r['baseline_units'] for r in valid); post_base=sum(r['post_baseline_units'] for r in valid)
            incremental=sum(r['incremental_units'] for r in valid); post_incremental=sum(r['post_incremental_units'] for r in valid)
            result.append(dict(method=method,customer_id=cid,category=category,cohort=cohort,
                total_promotions=len(group),cohort_promotions=len(selected),available_promotions=len(valid),
                unavailable_promotions=len(selected)-len(valid),censored_promotions=sum(r['censored'] for r in group),
                baseline_units=baseline,incremental_units=incremental,post_incremental_units=post_incremental,
                uplift_pct=ratio(incremental,baseline,True),post_dip_pct=ratio(post_incremental,post_base,True),
                net_uplift_pct=ratio(incremental+post_incremental,baseline,True)))
    return result
