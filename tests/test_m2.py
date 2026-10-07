import csv
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from fractions import Fraction
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fmcg.generate import ROOT
from fmcg.analytics.metrics import build,read,ratio,effects,service,export
from fmcg.dashboard import render

class CommercialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=ROOT/'data'
        if not (cls.data/'manifest.json').exists():
            from fmcg.generate import generate
            generate(ROOT/'config/scenario.toml',cls.data)
        cls.as_of=dt.date(2026,9,30); cls.report=build(cls.data,cls.as_of)
    def test_source_money_and_quantity_reconcile(self):
        for kind,table,qty,date in [('SO','fact_sales_daily','quantity','date'),('SI','fact_order_line','delivered_qty','delivered_date')]:
            raw=[r for r in read(self.data,table) if r[date] and '2026-01-01'<=r[date]<='2026-09-30']
            metrics=[r for r in self.report['sku_ytd'] if r['sales_type']==kind]
            self.assertEqual(sum(int(r['amount_satang']) for r in raw),sum(r['ty_amount_satang'] for r in metrics))
            self.assertEqual(sum(int(r[qty]) for r in raw),sum(r['ty_qty'] for r in metrics))
    def test_contribution_rank_and_exact_effects(self):
        for cid in ('C01','C02','C03'):
            for kind in ('SI','SO'):
                rows=[r for r in self.report['sku_ytd'] if r['customer_id']==cid and r['sales_type']==kind]
                self.assertEqual(sum(r['contribution_pct'] for r in rows),100)
                top=max(rows,key=lambda r:r['ty_amount_satang']); self.assertEqual(top['sku_rank'],1)
        for r in self.report['sku_ytd']:
            if r['sales_type']=='SO': self.assertEqual(r['volume_effect_satang']+r['price_effect_satang']+r['undecomposed_delta_satang'],r['ty_amount_satang']-r['ly_amount_satang'])
    def test_attainment_uses_ytd_not_annual_target(self):
        raw=read(self.data,'fact_target_monthly')
        for r in self.report['category_ytd']:
            if r['sales_type']=='SI':
                expected=sum(int(t['target_amount_satang']) for t in raw if t['customer_id']==r['customer_id'] and t['category']==r['category'] and '2026-01-01'<=t['month_start']<='2026-09-01')
                self.assertEqual(r['ytd_target_satang'],expected); self.assertEqual(r['target_attainment_pct'],Fraction(r['ty_amount_satang']*100,expected))
    def test_monthly_mom_crosses_year_and_quarter_reconciles(self):
        rows=self.report['monthly']; jan=next(r for r in rows if r['year']==2025 and r['month']==1); dec=next(r for r in rows if r['year']==2024 and r['month']==12 and r['customer_id']==jan['customer_id'] and r['product_id']==jan['product_id'] and r['sales_type']==jan['sales_type'])
        self.assertEqual(jan['mom_amount_pct'],Fraction((jan['amount_satang']-dec['amount_satang'])*100,dec['amount_satang']))
        for r in self.report['quarterly']:
            expected=sum(m['amount_satang'] for m in rows if m['year']==2026 and m['month'] in r['months'] and m['customer_id']==r['customer_id'] and m['category']==r['category'] and m['sales_type']==r['sales_type'])
            self.assertEqual(r['ty_amount_satang'],expected)
    def test_null_denominators_and_rational_decomposition(self):
        self.assertIsNone(ratio(1,0)); self.assertIsNone(ratio(0,0,True))
        e=effects(100,3,300,7); self.assertEqual(e['volume_effect_satang'],Fraction(400,3)); self.assertEqual(e['price_effect_satang'],Fraction(200,3)); self.assertEqual(sum(e.values()),200)
        e=effects(0,0,300,7); self.assertIsNone(e['volume_effect_satang']); self.assertEqual(e['undecomposed_delta_satang'],300)
    def test_tied_dense_rank_and_zero_sales_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'warehouse').mkdir(); (root/'manifest.json').write_text(json.dumps({'start_date':'2024-01-01','as_of_date':'2026-09-30'}))
            tables={'dim_customer':[dict(customer_id='A',customer_name='Demo')],'dim_store':[dict(store_id='S',customer_id='A')],'dim_product':[dict(product_id=p,product_name=p,brand='B',category='C') for p in ('P1','P2','P3')],'fact_sales_daily':[dict(date='2026-01-01',store_id='S',product_id=p,quantity=10,amount_satang=100) for p in ('P1','P2')],'fact_order_line':[],'fact_target_monthly':[]}
            for name,rows in tables.items():
                with (root/'warehouse'/f'{name}.csv').open('w',newline='') as stream:
                    w=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else ['unused']); w.writeheader(); w.writerows(rows)
            report=build(root,self.as_of); rows=[r for r in report['sku_ytd'] if r['sales_type']=='SO']
            self.assertEqual([r['sku_rank'] for r in rows],[1,1,2]); self.assertIsNone(rows[2]['ty_asp_satang']); self.assertIsNone(rows[0]['yoy_amount_pct'])
    def test_asof_bounds_and_no_future_deliveries_in_historical_report(self):
        with self.assertRaises(ValueError): build(self.data,dt.date(2026,9,15))
        with self.assertRaises(ValueError): build(self.data,dt.date(2026,12,31))
        old=build(self.data,dt.date(2025,9,30)); raw=read(self.data,'fact_order_line'); expected=sum(int(r['amount_satang']) for r in raw if r['delivered_date'] and '2025-01-01'<=r['delivered_date']<='2025-09-30')
        self.assertEqual(sum(r['ty_amount_satang'] for r in old['sku_ytd'] if r['sales_type']=='SI'),expected)
    def test_export_retains_exact_fraction_evidence_and_escapes_script(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp); export(self.report,output); evidence=json.loads((output/'price_volume_exact.json').read_text()); first=evidence[0]
            for key in ('volume_effect_satang','price_effect_satang'):
                v=first[key]; self.assertEqual(Fraction(int(v['numerator']),int(v['denominator'])),next(r for r in self.report['sku_ytd'] if r['customer_id']==first['customer_id'] and r['product_id']==first['product_id'] and r['sales_type']=='SO')[key])
            payload=json.loads((output/'analytics.json').read_text()); payload['data_class']='</script><script>alert(1)</script>'; (output/'analytics.json').write_text(json.dumps(payload)); path=render(output); self.assertNotIn('</script><script>alert',path.read_text())

class ServiceTests(unittest.TestCase):
    def test_due_cohort_cancelled_remainder_and_exact_p90(self):
        day=dt.date(2026,9,20)
        def line(order,promise,delivery,ordered,delivered,order_date=day): return dict(order_id=order,order_date=order_date,promised_date=promise,delivered_date=delivery,ordered_qty=ordered,delivered_qty=delivered)
        rows=[line('A',day+dt.timedelta(days=2),day+dt.timedelta(days=1),10,10),line('A',day+dt.timedelta(days=2),day+dt.timedelta(days=3),10,5),line('C',day+dt.timedelta(days=2),None,10,0),line('B',dt.date(2026,10,2),dt.date(2026,9,30),10,10,dt.date(2026,9,29)),line('D',dt.date(2026,10,5),None,20,0,dt.date(2026,9,30))]
        r=service(rows,dt.date(2026,9,30)); self.assertEqual(r['fill_rate_pct'],50); self.assertEqual(r['line_otif_pct'],Fraction(100,3)); self.assertEqual(r['order_otif_pct'],0); self.assertEqual(r['backlog_qty'],30); self.assertEqual(r['overdue_backlog_qty'],10); self.assertEqual(r['mean_lead_days'],Fraction(5,3)); self.assertEqual(r['p90_lead_days'],Fraction(13,5)); self.assertEqual(r['pending_lines'],2)
        historical=service(rows,dt.date(2026,9,21)); self.assertIsNone(historical['fill_rate_pct']); self.assertEqual(historical['backlog_qty'],20)
    def test_empty_and_single_delivery(self):
        r=service([],dt.date(2026,9,30)); self.assertIsNone(r['order_otif_pct']); self.assertIsNone(r['p90_lead_days']); self.assertEqual(r['backlog_qty'],0)

@unittest.skipUnless(os.environ.get('FMCG_TEST_DATABASE_URL'),'PostgreSQL M2 views parity requires isolated database')
class PostgreSQLM2Tests(unittest.TestCase):
    def test_sql_views_match_local_results(self):
        import psycopg
        from fmcg.load import load
        url=os.environ['FMCG_TEST_DATABASE_URL']; load(ROOT/'data',ROOT/'config/scenario.toml',url); report=build(ROOT/'data',dt.date(2026,9,30))
        from psycopg.rows import dict_row
        with psycopg.connect(url,row_factory=dict_row) as conn:
            for view,key,name in [('v_m2_monthly',('year','month','customer_id','product_id','sales_type'),'monthly'),('v_m2_sku_ytd',('customer_id','product_id','sales_type'),'sku_ytd'),('v_m2_category_ytd',('customer_id','category','sales_type'),'category_ytd'),('v_m2_service',('customer_id',),'service')]:
                expected={tuple(r[k] for k in key):r for r in report[name]}; sqlrows=conn.execute(f'SELECT * FROM fmcg.{view}').fetchall(); self.assertEqual(len(sqlrows),len(expected))
                for row in sqlrows:
                    local=expected[tuple(row[k] for k in key)]
                    for field,value in row.items():
                        if field not in local: continue
                        ref=local[field]
                        if ref is None: self.assertIsNone(value,field)
                        elif isinstance(ref,Fraction): self.assertLess(abs(Decimal(ref.numerator)/Decimal(ref.denominator)-value),Decimal('0.000001'),field)
                        else: self.assertEqual(value,ref,field)
