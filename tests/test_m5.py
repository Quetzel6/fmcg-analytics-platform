import csv
import datetime as dt
from fractions import Fraction
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from fmcg.risk.metrics import feature,build,summarize,DEFAULT_POLICY,load_policy
from fmcg.risk_validation import binary_metrics,evaluate
from fmcg.promotion_dashboard import render
ROOT=Path(__file__).resolve().parents[1];DAY=dt.timedelta(days=1)

class M5Tests(unittest.TestCase):
    def sample(self,closing=70,sold=10):
        day=dt.date(2026,2,1);history=[dict(day=day-i*DAY,sold=10,closing=100) for i in range(28,0,-1)]
        return history,dict(day=day,sold=sold,closing=closing)
    def test_cover_boundary_and_excess(self):
        history,current=self.sample();r=feature(history,current,DEFAULT_POLICY);self.assertEqual(r['days_of_cover'],7);self.assertFalse(r['risk_flag']);self.assertFalse(r['naive_flag'])
        current['closing']=69;self.assertTrue(feature(history,current,DEFAULT_POLICY)['risk_flag'])
        current['closing']=601;self.assertTrue(feature(history,current,DEFAULT_POLICY)['excess_stock']);policy=dict(DEFAULT_POLICY,excess_cover_days=61);self.assertFalse(feature(history,current,policy)['excess_stock'])
    def test_zero_demand_and_incomplete_history(self):
        history,current=self.sample();current['sold']=0
        for row in history:row['sold']=0
        r=feature(history,current,DEFAULT_POLICY);self.assertIsNone(r['days_of_cover']);self.assertIsNone(r['naive_flag']);self.assertIsNone(r['risk_flag'])
        r=feature(history[:10],current,DEFAULT_POLICY);self.assertFalse(r['history_complete']);self.assertEqual(r['risk_reason'],'incomplete_history')
    def test_weekday_censor_adjustment(self):
        history,current=self.sample(50)
        for row in history[-14:]:row.update(sold=0,closing=0)
        r=feature(history,current,DEFAULT_POLICY);self.assertEqual(r['uncensored_mean_daily'],10);self.assertTrue(r['risk_flag']);self.assertFalse(r['naive_flag'])
    def test_missing_uncensored_weekday(self):
        history,current=self.sample()
        for row in history:
            if row['day'].weekday()==0:row['closing']=0
        self.assertIsNone(feature(history,current,DEFAULT_POLICY)['risk_score'])
    def test_prior_only_lost_sales(self):
        history,current=self.sample(0,3);r=feature(history,current,DEFAULT_POLICY);self.assertEqual(r['estimated_lost_units'],7)
        current['closing']=1;self.assertEqual(feature(history,current,DEFAULT_POLICY)['estimated_lost_units'],0)
        self.assertIsNone(feature(history[1:],current,DEFAULT_POLICY)['estimated_lost_units'])
    def test_future_history_ignored(self):
        history,current=self.sample();expected=feature(history,current,DEFAULT_POLICY);history.append(dict(day=current['day']+DAY,sold=99999,closing=0));self.assertEqual(expected,feature(history,current,DEFAULT_POLICY))
    def test_missing_history_date(self):
        history,current=self.sample();history[-5]['day']=history[-6]['day'];self.assertFalse(feature(history,current,DEFAULT_POLICY)['history_complete'])
    def test_metrics_tied_scores(self):
        r=binary_metrics([(Fraction(1),True,True),(Fraction(1),True,False),(Fraction(0),False,True)])
        self.assertEqual(r['precision'],Fraction(1,2));self.assertEqual(r['recall'],Fraction(1,2));self.assertEqual(r['average_precision'],Fraction(7,12));self.assertEqual(r['pr_auc'],Fraction(2,3));self.assertEqual(r['tn'],0)
    def test_metrics_edge_cases(self):
        r=binary_metrics([]);self.assertIsNone(r['precision']);self.assertIsNone(r['pr_auc'])
        r=binary_metrics([(Fraction(0),False,False)]);self.assertIsNone(r['recall']);self.assertIsNone(r['average_precision'])
        r=binary_metrics([(Fraction(0),False,True)]);self.assertEqual(r['recall'],0);self.assertIsNone(r['precision'])
        r=binary_metrics([(Fraction(1),True,True),(Fraction(0),False,False)]);self.assertEqual(r['pr_auc'],1)
    def test_labels_exclusive_current_and_complete_future(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'truth').mkdir();rows=[];day=dt.date(2026,1,1)
            for i in range(8):
                rows.append(dict(date=str(day+i*DAY),store_id='S',product_id='P',customer_id='C',category='Cat',history_complete=True,risk_score=Fraction(1),risk_flag=True,naive_score=Fraction(1),naive_flag=True,observed_stockout=i==0,estimated_lost_units=Fraction(0)))
            p=root/'truth/truth_demand_daily.csv'
            def write(last,current_loss=5):
                with p.open('w',newline='') as stream:
                    w=csv.DictWriter(stream,fieldnames=['date','store_id','product_id','lost_qty']);w.writeheader();w.writerows(dict(date=r['date'],store_id='S',product_id='P',lost_qty=current_loss if i==0 else 5 if last and i==7 else 0) for i,r in enumerate(rows))
            write(False);metrics,loss,availability=evaluate(root,rows,DEFAULT_POLICY);self.assertEqual(metrics[0]['samples'],1);self.assertEqual(metrics[0]['positives'],0)
            write(True);self.assertEqual(evaluate(root,rows,DEFAULT_POLICY)[0][0]['positives'],1)
            self.assertEqual(evaluate(root,rows[:-1],DEFAULT_POLICY)[0][0]['eligible_days'],0)
            write(False,0);self.assertEqual(evaluate(root,rows,DEFAULT_POLICY)[2][0]['proxy_fp'],1)
    def test_config_protocol(self):
        self.assertEqual(load_policy(ROOT/'config/risk.toml'),DEFAULT_POLICY)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'risk.toml';p.write_text((ROOT/'config/risk.toml').read_text().replace('horizon_days = 7','horizon_days = 8'))
            with self.assertRaises(ValueError):load_policy(p)
    def test_cutoff_and_future_mutation(self):
        cutoff=dt.date(2024,2,1);expected=build(ROOT/'data',cutoff)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);warehouse=root/'warehouse';warehouse.mkdir()
            for name in ['dim_store','dim_product']:shutil.copy(ROOT/'data/warehouse'/f'{name}.csv',warehouse/f'{name}.csv')
            source=ROOT/'data/warehouse/fact_inventory_daily.csv'
            with source.open(newline='') as inp,(warehouse/source.name).open('w',newline='') as out:
                reader=csv.DictReader(inp);writer=csv.DictWriter(out,fieldnames=reader.fieldnames);writer.writeheader()
                for r in reader:
                    if r['date']>str(cutoff):r['sold_qty']='99999';r['closing_qty']='0'
                    writer.writerow(r)
            self.assertEqual(build(root,cutoff),expected)
        self.assertEqual(len(expected),32*150)
    def test_default_exports_coverage(self):
        payload=json.loads((ROOT/'output/m5/risk.json').read_text());self.assertEqual(len(payload['latest']),150);self.assertEqual(len(payload['monthly']),33*12)
        self.assertEqual(sum(r['store_sku_days'] for r in payload['monthly']),150600)
        self.assertTrue(all(r['date']=='2026-09-30' for r in payload['latest']))
        for r in payload['risk_validation']:
            self.assertEqual(r['eligible_days'],r['samples']+r['unscored_days']);self.assertNotIn('accuracy',r)
    def test_dashboard_embedding(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'data.json';source.write_text('{"x":"</script><script>bad()</script>"}');target=p/'page.html';render(source,ROOT/'dashboard/m5.html',target);self.assertNotIn('</script><script>bad()',target.read_text());self.assertIn('\\u003c',target.read_text())
    def test_boundary(self):
        for p in (ROOT/'src/fmcg/risk').glob('*.py'):
            self.assertNotIn('truth',p.read_text());self.assertNotIn('risk_validation',p.read_text())

if __name__=='__main__':unittest.main()
