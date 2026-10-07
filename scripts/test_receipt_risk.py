import csv
import datetime as dt
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from fmcg.generate import ROOT
from fmcg.risk.receipts import load_policy, parse_order, project
from fmcg.receipt_validation import evaluate
from fmcg.receipt_scenario import render

DAY=dt.timedelta(days=1)


class ReceiptRiskTests(unittest.TestCase):
    def setUp(self):
        self.day=dt.date(2027,1,1)
        self.policy=load_policy(ROOT/'config/receipt_risk_v1.toml')

    def order(self, placed=-1, promised=1, delivered=None, quantity=100):
        return dict(order_date=self.day+placed*DAY,promised_date=self.day+promised*DAY,
                    delivered_date=self.day+delivered*DAY if delivered is not None else None,
                    ordered_qty=quantity)

    def test_without_receipts_matches_cover_score(self):
        result=project(self.day,50,Fraction(10),[],self.policy)
        self.assertEqual(result['receipt_score'],Fraction(70,120))
        self.assertTrue(result['receipt_flag'])

    def test_promised_receipt_reduces_alert(self):
        result=project(self.day,50,Fraction(10),[self.order()],self.policy)
        self.assertEqual(result['credited_receipt_qty'],80)
        self.assertFalse(result['receipt_flag'])

    def test_late_receipt_does_not_hide_earlier_shortage(self):
        result=project(self.day,10,Fraction(10),[self.order(promised=3)],self.policy)
        self.assertEqual(result['minimum_projected_qty'],-10)
        self.assertTrue(result['receipt_flag'])

    def test_future_created_and_received_lines_excluded(self):
        result=project(self.day,50,Fraction(10),
                       [self.order(placed=1),self.order(delivered=0)],self.policy)
        self.assertEqual(result['known_open_lines'],0)
        self.assertEqual(result['credited_receipt_qty'],0)

    def test_overdue_and_beyond_horizon_not_credited(self):
        result=project(self.day,50,Fraction(10),
                       [self.order(promised=0),self.order(promised=8)],self.policy)
        self.assertEqual(result['overdue_ordered_qty'],100)
        self.assertEqual(result['credited_receipt_qty'],0)

    def test_future_delivery_outcomes_do_not_change_predictions(self):
        one=project(self.day,50,Fraction(10),[self.order(delivered=2)],self.policy)
        two=project(self.day,50,Fraction(10),[self.order(delivered=20)],self.policy)
        unknown=project(self.day,50,Fraction(10),[self.order()],self.policy)
        self.assertEqual(one,two);self.assertEqual(two,unknown)
        row=dict(order_date='2026-12-31',promised_date='2027-01-02',
                 delivered_date='2027-01-05',ordered_qty='100',delivered_qty='1')
        first=parse_order(row);row['delivered_qty']='10000'
        self.assertEqual(first,parse_order(row))

    def test_missing_demand_stays_unscored(self):
        self.assertIsNone(project(self.day,50,None,[self.order()],self.policy)['receipt_score'])
        self.assertIsNone(project(self.day,50,Fraction(0),[],self.policy)['receipt_flag'])

    def test_invalid_fraction_and_period_rejected(self):
        original=(ROOT/'config/receipt_risk_v1.toml').read_text()
        for changed in (original.replace('receipt_denominator = 5','receipt_denominator = 0'),
                        original.replace('2027-01-01','2026-01-01'),
                        original.replace('receipt_numerator = 4','receipt_numerator = 5')):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'policy.toml';path.write_text(changed)
                with self.assertRaises(ValueError):load_policy(path)

    def test_only_complete_reserved_future_labels_evaluated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'truth').mkdir()
            rows=[]
            with (root/'truth/truth_demand_daily.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=['date','store_id','product_id','lost_qty']);writer.writeheader()
                for i in range(-1,9):
                    date=str(self.day+i*DAY)
                    writer.writerow(dict(date=date,store_id='S',product_id='P',lost_qty=1 if i==4 else 0))
                    rows.append(dict(date=date,store_id='S',product_id='P',history_complete=True,
                                     risk_score=Fraction(3,4),risk_flag=True,
                                     receipt_score=Fraction(1,4),receipt_flag=False))
            metrics=evaluate(root,rows,self.policy)
            self.assertEqual([r['samples'] for r in metrics],[2,2])
            self.assertEqual([r['positives'] for r in metrics],[2,2])
            self.assertEqual(metrics[0]['incomplete_future_days'],7)
            self.assertEqual(metrics[1]['fn'],2)

    def test_html_contains_both_methods_and_correct_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=[dict(method=m,samples=10,precision=Fraction(1,2),recall=Fraction(3,4),
                       pr_auc=Fraction(1,4),fp=2) for m in ('weekday_uncensored_cover','promised_receipt_path_v1')]
            render(dict(metrics=rows),Path(tmp))
            text=(Path(tmp)/'benchmark.html').read_text()
            self.assertIn('50.00%',text)
            self.assertIn('promised_receipt_path_v1',text)
            self.assertIn('../../index.html',text)


if __name__=='__main__':unittest.main()
