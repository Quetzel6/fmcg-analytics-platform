import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fmcg.generate import generate,ROOT,sha256
from fmcg.validate import validate
from fmcg.contracts import COLUMNS,csv_path

class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name); cls.data=cls.root/'data'; cls.config=ROOT/'config/scenario.toml'; cls.manifest=generate(cls.config,cls.data)
        cls.original={t:csv_path(cls.data,t).read_bytes() for t in COLUMNS}; cls.manifest_bytes=(cls.data/'manifest.json').read_bytes()
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def tearDown(self):
        for table,content in self.original.items():
            path=csv_path(self.data,table)
            if path.read_bytes()!=content: path.write_bytes(content)
        (self.data/'manifest.json').write_bytes(self.manifest_bytes)
    def mutate(self,table,callback):
        path=csv_path(self.data,table)
        with path.open(newline='') as stream: rows=list(csv.DictReader(stream))
        callback(rows)
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=COLUMNS[table],lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    def assert_dq(self,code,config=None,strict=True):
        report,_=validate(self.data,config or self.config,strict)
        found=next(r for r in report['rules'] if r['id']==code)
        self.assertGreater(found['count'],0,report); return report
    def test_full_contract_and_strict_sanity(self):
        report,_=validate(self.data,self.config,True); self.assertEqual(report['status'],'passed',report)
        for table in ('fact_sales_daily','fact_inventory_daily','truth_demand_daily'): self.assertEqual(self.manifest['files'][table]['rows'],150600)
        self.assertEqual(self.manifest['files']['dim_date']['rows'],1004)
    def test_ground_truth_counterfactual_coupling(self):
        report,tables=validate(self.data,self.config,True)
        active={}; customer={r['store_id']:r['customer_id'] for r in tables['dim_store']}
        for p in tables['dim_promotion']:
            day=p['start_date']
            while day<=p['end_date']:
                active[day,p['customer_id'],p['product_id']]='up'; day+=dt.timedelta(days=1)
            for offset in range(1,15): active[p['end_date']+dt.timedelta(days=offset),p['customer_id'],p['product_id']]='down'
        for r in tables['truth_demand_daily']:
            effect=active.get((r['date'],customer[r['store_id']],r['product_id']))
            if effect=='up': self.assertGreaterEqual(r['latent_demand_qty'],r['baseline_demand_qty'])
            elif effect=='down': self.assertLessEqual(r['latent_demand_qty'],r['baseline_demand_qty'])
            else: self.assertEqual(r['latent_demand_qty'],r['baseline_demand_qty'])
    def test_seed_config_code_and_pinned_numpy_reproduce_all_checksums(self):
        other=self.root/'repeat'; repeat=generate(self.config,other)
        self.assertEqual(self.manifest,repeat)
        changed=self.root/'changed.toml'; changed.write_text(self.config.read_text().replace('seed = 20261005','seed = 20261006')); different=generate(changed,self.root/'different')
        self.assertNotEqual(self.manifest['files']['fact_sales_daily']['sha256'],different['files']['fact_sales_daily']['sha256'])
    def test_dq01_duplicate_and_null(self):
        self.mutate('dim_customer',lambda rows:rows.append(dict(rows[0]))); self.assert_dq('DQ-01')
        csv_path(self.data,'dim_customer').write_bytes(self.original['dim_customer'])
        self.mutate('dim_product',lambda rows:rows[0].update(product_name='')); self.assert_dq('DQ-01')
    def test_dq02_orphan_fk(self):
        self.mutate('fact_sales_daily',lambda rows:rows[0].update(store_id='UNKNOWN')); self.assert_dq('DQ-02')
    def test_dq03_negative_quantity(self):
        self.mutate('fact_sales_daily',lambda rows:rows[0].update(quantity='-1')); self.assert_dq('DQ-03')
    def test_dq04_future_observed_actual(self):
        self.mutate('fact_sales_daily',lambda rows:rows[0].update(date='2026-10-01')); self.assert_dq('DQ-04')
    def test_dq05_missing_panel_row(self):
        self.mutate('fact_sales_daily',lambda rows:rows.pop()); self.assert_dq('DQ-05')
    def test_dq06_exact_amount(self):
        self.mutate('fact_sales_daily',lambda rows:rows[0].update(amount_satang=str(int(rows[0]['amount_satang'])+1))); self.assert_dq('DQ-06')
    def test_dq07_realised_price(self):
        def change(rows):
            row=rows[0]; row['unit_price_satang']=str(int(row['unit_price_satang'])+1); row['amount_satang']=str(int(row['quantity'])*int(row['unit_price_satang']))
        self.mutate('fact_sales_daily',change); self.assert_dq('DQ-07')
    def test_dq08_stock_identity(self):
        self.mutate('fact_inventory_daily',lambda rows:rows[0].update(closing_qty=str(int(rows[0]['closing_qty'])+1))); self.assert_dq('DQ-08')
    def test_dq09_opening_continuity(self):
        def change(rows):
            row=rows[150]; row['opening_qty']=str(int(row['opening_qty'])+1); row['closing_qty']=str(int(row['closing_qty'])+1)
        self.mutate('fact_inventory_daily',change); self.assert_dq('DQ-09')
    def test_dq10_sales_stock_reconcile(self):
        self.mutate('fact_inventory_daily',lambda rows:rows[0].update(sold_qty=str(int(rows[0]['sold_qty'])+1))); self.assert_dq('DQ-10')
    def test_dq11_receipts_delivery_reconcile(self):
        self.mutate('fact_inventory_daily',lambda rows:rows[0].update(receipt_qty=str(int(rows[0]['receipt_qty'])+1))); self.assert_dq('DQ-11')
    def test_dq12_short_ship_open_rules(self):
        self.mutate('fact_order_line',lambda rows:rows[0].update(delivered_date='')); self.assert_dq('DQ-12')
    def test_dq13_overlap(self):
        def change(rows):
            row=dict(rows[0]); row['promo_id']='OVERLAP'; rows.append(row)
        self.mutate('dim_promotion',change); self.assert_dq('DQ-13')
    def test_dq14_price_version_coverage(self):
        self.mutate('dim_price',lambda rows:rows.pop(0)); self.assert_dq('DQ-14')
    def test_dq15_future_target_coverage(self):
        self.mutate('fact_target_monthly',lambda rows:rows.pop()); self.assert_dq('DQ-15')
    def test_dq16_manifest_counts_checksums_totals(self):
        manifest=json.loads(self.manifest_bytes); manifest['files']['fact_sales_daily']['rows']+=1; manifest['files']['fact_sales_daily']['sha256']='tampered'; manifest['amount_totals_satang']['fact_sales_daily']+=1
        (self.data/'manifest.json').write_text(json.dumps(manifest)); report=self.assert_dq('DQ-16'); rule=next(r for r in report['rules'] if r['id']=='DQ-16'); self.assertGreaterEqual(rule['count'],3)
    def test_dq17_warn_in_loader_error_in_tests(self):
        config=self.root/'impossible.toml'; config.write_text(self.config.read_text().replace('stockout_max = 0.08','stockout_max = 0.00001'))
        manifest=json.loads(self.manifest_bytes); manifest['config_sha256']=sha256(config); (self.data/'manifest.json').write_text(json.dumps(manifest))
        strict=self.assert_dq('DQ-17',config,True); warning=self.assert_dq('DQ-17',config,False)
        self.assertEqual(strict['status'],'failed'); self.assertEqual(warning['status'],'passed')
    def test_forecast_targets_and_open_promises_can_exceed_as_of(self):
        report,tables=validate(self.data,self.config,True); end=dt.date(2026,9,30)
        self.assertTrue(any(r['month_start']>end for r in tables['fact_target_monthly'])); self.assertTrue(any(r['promised_date']>end for r in tables['fact_order_line'])); self.assertEqual(report['status'],'passed')
    def test_loader_aborts_invalid_data_before_connect(self):
        from fmcg.load import load
        self.mutate('fact_sales_daily',lambda rows:rows[0].update(quantity='-1'))
        with self.assertRaisesRegex(ValueError,'Data-quality gate failed'): load(self.data,self.config,'unused')
    def test_order_otif_inequality_counterexample(self):
        orders=[[True]]*9+[[False]*10]
        order_rate=sum(all(lines) for lines in orders)/len(orders)
        line_rate=sum(sum(lines) for lines in orders)/sum(map(len,orders))
        self.assertGreater(order_rate,line_rate)
    def test_analytics_truth_boundary(self):
        # Mandatory guard for later M2-M5 modules. Generator, loader and QA are excluded.
        for folder in ('analytics','forecast','uplift','risk'):
            for path in (ROOT/'src/fmcg'/folder).rglob('*'):
                if path.suffix in ('.py','.sql'):
                    text=path.read_text().lower(); self.assertNotIn('truth',text,str(path))

@unittest.skipUnless(os.environ.get('FMCG_TEST_DATABASE_URL'),'No isolated PostgreSQL supplied; integration remains unverified')
class PostgreSQLIntegration(unittest.TestCase):
    def test_snapshot_repeat_and_transaction_rollback(self):
        import psycopg
        from fmcg.load import load
        url=os.environ['FMCG_TEST_DATABASE_URL']
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'data'; generate(ROOT/'config/scenario.toml',data)
            first=load(data,ROOT/'config/scenario.toml',url); second=load(data,ROOT/'config/scenario.toml',url)
            self.assertEqual(first['post_load'],second['post_load'])
            def fail_after_inserts(conn,tables): raise RuntimeError('Injected failure before commit')
            with patch('fmcg.load.database_reconcile',fail_after_inserts):
                with self.assertRaises(RuntimeError): load(data,ROOT/'config/scenario.toml',url)
            with psycopg.connect(url) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM fmcg.fact_sales_daily').fetchone()[0],150600)
                self.assertEqual(str(conn.execute('SELECT SUM(amount_satang::NUMERIC) FROM fmcg.fact_sales_daily').fetchone()[0]),first['post_load']['amount_totals_satang']['fact_sales_daily'])
