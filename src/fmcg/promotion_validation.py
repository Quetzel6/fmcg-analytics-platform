"""M4 validation-only comparison with planted demand effects."""
import csv
from fractions import Fraction

def evaluate(root,estimates):
    with (root/'truth/truth_promo_effect.csv').open(newline='') as stream:
        planted={r['promo_id']:r for r in csv.DictReader(stream)}
    rows=[]; summary=[]
    for row in estimates:
        if row['status']!='available': continue
        effect=planted[row['promo_id']]
        rows.append(dict(promo_id=row['promo_id'],method=row['method'],censored=row['censored'],post_censored=row['post_censored'],
            uplift_error_pp=row['uplift_pct']-Fraction(effect['true_uplift_pct']),
            post_dip_error_pp=row['post_dip_pct']-Fraction(effect['true_post_dip_pct'])))
    for method in ('B1','B2'):
        for cohort in ('all','uncensored'):
            uplift=[r['uplift_error_pp'] for r in rows if r['method']==method and (cohort=='all' or not r['censored'])]
            dip=[r['post_dip_error_pp'] for r in rows if r['method']==method and (cohort=='all' or not r['post_censored'])]
            summary.append(dict(method=method,cohort=cohort,uplift_count=len(uplift),post_dip_count=len(dip),
                uplift_bias_pp=sum(uplift)/len(uplift) if uplift else None,
                uplift_mae_pp=sum(abs(v) for v in uplift)/len(uplift) if uplift else None,
                post_dip_bias_pp=sum(dip)/len(dip) if dip else None,
                post_dip_mae_pp=sum(abs(v) for v in dip)/len(dip) if dip else None))
    return rows,summary
