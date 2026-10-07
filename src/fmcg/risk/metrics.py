"""Past-only stock coverage, proxy availability and fixed risk rules."""
import datetime as dt
import tomllib
from collections import defaultdict
from fractions import Fraction
from ..analytics.metrics import read,ratio

DAY=dt.timedelta(days=1)
DEFAULT_POLICY=dict(lookback_days=28,horizon_days=7,excess_cover_days=60,heldout_start='2026-01-01',method='weekday_uncensored_cover')

def load_policy(path):
    with path.open('rb') as stream: policy=tomllib.load(stream)['risk']
    if policy['lookback_days']!=28 or policy['horizon_days']!=7 or policy['method']!='weekday_uncensored_cover':
        raise ValueError('M5 protocol requires 28-day history and 7-day weekday-uncensored cover')
    if not isinstance(policy['excess_cover_days'],int) or policy['excess_cover_days']<=0: raise ValueError('Excess threshold must be a positive integer')
    dt.date.fromisoformat(policy['heldout_start'])
    return policy

def feature(history,current,policy):
    """History excludes current; all rows have date <= current date."""
    day=current['day']; recent=[r for r in history if day-28*DAY<=r['day']<day]
    inclusive=[r for r in recent if r['day']>=day-27*DAY]+[current]
    expected_dates={day-i*DAY for i in range(28)}
    full=len(inclusive)==28 and {r['day'] for r in inclusive}==expected_dates
    mean=Fraction(sum(r['sold'] for r in inclusive),28) if full else None
    cover=Fraction(current['closing'],mean) if mean else None
    weekday=defaultdict(list)
    if full:
        for r in inclusive:
            if r['closing']>0: weekday[r['day'].weekday()].append(r['sold'])
    adjusted= sum((Fraction(sum(weekday[w]),len(weekday[w])) for w in range(7)),Fraction())/7 if len(weekday)==7 else None
    adjusted_cover=Fraction(current['closing'],adjusted) if adjusted else None
    # Score decreases monotonically with cover; score > 1/2 exactly means cover < 7.
    score=Fraction(7*adjusted,current['closing']+7*adjusted) if adjusted else None
    naive_score=Fraction(7*mean,current['closing']+7*mean) if mean else None
    prior_full=len(recent)==28 and {r['day'] for r in recent}=={day-i*DAY for i in range(1,29)}
    matches=[r['sold'] for r in recent if r['day'].weekday()==day.weekday() and r['closing']>0]
    loss=None
    if prior_full:
        if current['closing']>0: loss=Fraction(0)
        elif matches: loss=max(Fraction(sum(matches),len(matches))-current['sold'],Fraction(0))
    return dict(history_complete=full,mean_sold_28=mean,days_of_cover=cover,
        observed_stockout=current['closing']==0,excess_stock=cover>policy['excess_cover_days'] if cover is not None else None,
        uncensored_mean_daily=adjusted,adjusted_days_of_cover=adjusted_cover,
        risk_flag=adjusted_cover<7 if adjusted_cover is not None else None,risk_score=score,
        naive_flag=cover<7 if cover is not None else None,naive_score=naive_score,
        risk_reason='available' if adjusted_cover is not None else 'incomplete_history' if not full else 'missing_weekday_or_zero_demand',
        estimated_lost_units=loss)

def build(root,as_of=dt.date(2026,9,30),policy=None):
    policy=policy or DEFAULT_POLICY
    stores={r['store_id']:r['customer_id'] for r in read(root,'dim_store')}
    products={r['product_id']:r for r in read(root,'dim_product')}
    panels=defaultdict(list)
    for row in read(root,'fact_inventory_daily'):
        day=dt.date.fromisoformat(row['date'])
        if day<=as_of: panels[row['store_id'],row['product_id']].append(dict(day=day,sold=int(row['sold_qty']),closing=int(row['closing_qty'])))
    output=[]
    for (sid,pid),panel in sorted(panels.items()):
        history=[]
        for current in sorted(panel,key=lambda r:r['day']):
            values=feature(history,current,policy)
            output.append(dict(date=str(current['day']),store_id=sid,customer_id=stores[sid],product_id=pid,
                product_name=products[pid]['product_name'],category=products[pid]['category'],sold_qty=current['sold'],closing_qty=current['closing'],**values))
            history.append(current);history=history[-28:]
    return output

def summarize(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['date'][:7],r['customer_id'],r['category']].append(r)
    output=[]
    for (month,cid,category),group in sorted(groups.items()):
        stockouts=sum(r['observed_stockout'] for r in group)
        output.append(dict(month=month,customer_id=cid,category=category,store_sku_days=len(group),stockout_days=stockouts,
            availability_pct=ratio(len(group)-stockouts,len(group),True),cover_available_days=sum(r['days_of_cover'] is not None for r in group),
            excess_days=sum(r['excess_stock'] is True for r in group),risk_available_days=sum(r['risk_flag'] is not None for r in group),
            risk_flag_days=sum(r['risk_flag'] is True for r in group)))
    return output
