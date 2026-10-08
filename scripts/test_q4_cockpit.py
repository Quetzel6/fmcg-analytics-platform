"""Presentation safety, ledger reconciliation and order-state checks."""
import copy
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from fmcg.generate import ROOT
from fmcg.planning.bridge import build, load_plan
from fmcg.planning.cockpit import actions, money, render, validate


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.table = None; self.rows = {}; self.external = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.table = attrs['id']; self.rows[self.table] = []
        if tag == 'tr' and 'data-scenario' in attrs:
            self.rows[self.table].append(attrs)
        if attrs.get('src') or (tag == 'link' and attrs.get('href')):
            self.external.append(attrs)
    def handle_endtag(self, tag):
        if tag == 'table': self.table = None


class CockpitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build(ROOT/'data', load_plan(ROOT/'config/q4_plan_v1.toml'))

    def test_all_customer_category_month_rows_have_filter_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            render(self.result, Path(tmp)); page = (Path(tmp)/'cockpit.html').read_text()
        parsed = Rows(); parsed.feed(page)
        self.assertEqual(len(parsed.rows['monthly']), 108)
        self.assertEqual(len(parsed.rows['orders']), 12)
        self.assertEqual(len(parsed.rows['annual']), 12)
        self.assertEqual(parsed.external, [])
        for scenario in ('conservative', 'central', 'optimistic'):
            monthly = [r for r in parsed.rows['monthly'] if r['data-scenario'] == scenario]
            self.assertEqual(len(monthly), 36)
            for cid in ('C01', 'C02', 'C03'):
                self.assertEqual(sum(r['data-customer'] == cid for r in monthly), 12)

    def test_no_order_has_no_operational_dates(self):
        result = copy.deepcopy(self.result)
        row = result['promotions'][0]
        row.update(delivered_cases=0, requested_order_cases=0, additional_delivered_si_units=0,
                   additional_q4_si_satang=0, additional_q1_si_satang=0)
        action = actions(result)[0]
        self.assertEqual(action['planning_state'], 'No incremental order')
        self.assertEqual(action['order_date'], '')
        self.assertEqual(action['expected_receipt_date'], '')

    def test_flags_expose_capacity_unserved_q1_and_stock(self):
        result = copy.deepcopy(self.result)
        result['promotions'][0].update(capacity_limited=True, unserved_positive_delta_so_units=1,
            additional_q1_si_satang=100, post_end_date='2027-01-14', closing_delta_stock_units=1)
        flags = actions(result)[0]['review_flags']
        for expected in ('Capacity limited', 'Unserved incremental SO', 'Receipt in Q1',
                         'Post period crosses into Q1', 'Residual incremental stock'):
            self.assertIn(expected, flags)

    def test_invalid_money_identity_and_duplicate_groups_block_export(self):
        validate(self.result)
        for mutation in ('amount', 'duplicate', 'annual', 'delivery'):
            result = copy.deepcopy(self.result)
            if mutation == 'amount': result['monthly'][0]['scenario_si_satang'] += 1
            elif mutation == 'duplicate': result['monthly'].append(result['monthly'][0])
            elif mutation == 'annual': result['outlook'][0]['scenario_gap_satang'] += 1
            else: result['promotions'][0]['additional_q4_si_satang'] += 1
            with self.assertRaises(ValueError): validate(result)

    def test_names_are_escaped_without_template_replacement(self):
        result = copy.deepcopy(self.result)
        result['promotions'][0]['product_name'] = '<script>alert("MONTHLY")</script>'
        result['baseline_outlook'][1]['customer_name'] = 'ANNUAL <img src=x onerror=alert(1)>'
        with tempfile.TemporaryDirectory() as tmp:
            render(result, Path(tmp)); page = (Path(tmp)/'cockpit.html').read_text()
        self.assertIn('&lt;script&gt;alert(&quot;MONTHLY&quot;)&lt;/script&gt;', page)
        self.assertIn('ANNUAL &lt;img', page)
        self.assertNotIn('<img src=x', page)

    def test_currency_keeps_precision_for_large_exact_values(self):
        self.assertEqual(money(100000000000000001), '1,000,000,000,000,000.01')
        self.assertEqual(money(-12345), '-123.45')


if __name__ == '__main__': unittest.main()
