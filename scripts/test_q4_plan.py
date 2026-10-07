from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from fmcg.generate import ROOT
from fmcg.planning.bridge import load_plan, simulate, build


class Q4PlanningTests(unittest.TestCase):
    def setUp(self):
        self.plan=load_plan(ROOT/'config/q4_plan_v1.toml')
        self.policy=dict(self.plan['planning'],incrementality_fraction='1',reserve_days=1,minimum_order_cases=1)
        self.promo=dict(self.plan['promotions'][0],baseline_so_units_per_day=10,
                        start_date='2026-10-12',end_date='2026-10-12',maximum_order_cases=100)
        self.scenario=dict(name='test',effect_multiplier='1',delivery_delay_days=0)
        self.effect=dict(gross_rate=Fraction(1),post_rate=Fraction(0),promotions=8,censored=3)

    def run_plan(self,stock=0,case=12,invoice=100):
        return simulate(self.promo,self.scenario,self.policy,self.effect,stock,case,invoice)

    def test_zero_effect_leaves_baseline_without_order(self):
        self.effect.update(gross_rate=Fraction(0),post_rate=Fraction(0))
        row=self.run_plan()
        self.assertEqual(row['additional_q4_si_satang'],0)
        self.assertEqual(row['delivered_cases'],0)

    def test_slack_stock_is_used_before_incremental_orders(self):
        row=self.run_plan(stock=30)
        self.assertEqual(row['opening_slack_units'],20)
        self.assertEqual(row['delivered_cases'],0)
        self.assertEqual(row['closing_delta_stock_units'],10)

    def test_case_rounding_and_minimum(self):
        self.policy['minimum_order_cases']=2
        row=self.run_plan()
        self.assertEqual(row['delivered_cases'],2)
        self.assertEqual(row['additional_delivered_si_units'],24)
        self.assertEqual(row['additional_si_satang'],2400)

    def test_capacity_limit_and_unserved_increment(self):
        self.promo['maximum_order_cases']=1
        self.effect['gross_rate']=Fraction(10)
        row=self.run_plan()
        self.assertTrue(row['capacity_limited'])
        self.assertEqual(row['unserved_positive_delta_so_units'],88)

    def test_late_delivery_does_not_backfill_lost_increment(self):
        self.scenario['delivery_delay_days']=2
        row=self.run_plan()
        self.assertEqual(row['unserved_positive_delta_so_units'],10)
        self.assertEqual(row['fulfilled_positive_delta_so_units'],0)
        self.assertEqual(row['closing_delta_stock_units'],12)

    def test_q1_receipts_do_not_close_q4_gap(self):
        self.promo.update(start_date='2026-12-31',end_date='2026-12-31')
        self.scenario['delivery_delay_days']=2
        row=self.run_plan()
        self.assertEqual(row['additional_q4_si_satang'],0)
        self.assertEqual(row['additional_q1_si_satang'],1200)

    def test_post_dip_and_stock_ledger_reconcile(self):
        self.effect['post_rate']=Fraction(-1,10)
        row=self.run_plan()
        self.assertEqual(row['avoided_baseline_so_units'],14)
        self.assertEqual(row['closing_delta_stock_units'],16)
        self.assertEqual(row['opening_slack_units']+row['additional_delivered_si_units']+
                         row['avoided_baseline_so_units']-row['fulfilled_positive_delta_so_units'],
                         row['closing_delta_stock_units'])

    def test_negative_delta_cannot_exceed_baseline_demand(self):
        self.effect['post_rate']=Fraction(-10)
        row=self.run_plan()
        self.assertEqual(row['avoided_baseline_so_units'],140)

    def test_bad_calendar_duplicate_sku_and_delay_are_rejected(self):
        original=(ROOT/'config/q4_plan_v1.toml').read_text()
        changes=[original.replace('2026-10-12','2026-10-01'),
                 original.replace('product_id = "P03"','product_id = "P01"'),
                 original.replace('delivery_delay_days = 3','delivery_delay_days = 15')]
        for text in changes:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'plan.toml';path.write_text(text)
                with self.assertRaises(ValueError):load_plan(path)

    def test_actual_plan_monthly_and_annual_money_reconcile(self):
        report=build(ROOT/'data',self.plan)
        self.assertEqual(len(report['monthly']),108)
        for name in ('conservative','central','optimistic'):
            monthly=sum(r['additional_si_satang'] for r in report['monthly'] if r['scenario']==name)
            all_row=next(r for r in report['outlook'] if r['scenario']==name and r['customer_id']=='ALL')
            self.assertEqual(monthly,all_row['additional_q4_si_satang'])
            self.assertEqual(all_row['scenario_full_year_satang']+all_row['scenario_gap_satang'],
                             all_row['annual_target_satang'])
        self.assertEqual(report['baseline_selection'],'ly_ytd_growth')


if __name__=='__main__':unittest.main()
