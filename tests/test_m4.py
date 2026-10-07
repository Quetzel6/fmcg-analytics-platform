import datetime as dt
import json
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from fmcg.uplift.estimators import estimate,dates,summarize,build
from fmcg.promotion_validation import evaluate
from fmcg.promotion_report import export
from fmcg.promotion_dashboard import render

ROOT=Path(__file__).resolve().parents[1]
class M4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows=build(ROOT/'data')
    def fixture(self):
        start=dt.date(2026,2,2);pre=dates(start-dt.timedelta(days=28),start-dt.timedelta(days=1));promo=dates(start,start+dt.timedelta(days=6));post=dates(promo[-1]+dt.timedelta(days=1),promo[-1]+dt.timedelta(days=14))
        return pre,promo,post
    def test_b1_known_uplift_dip_net(self):
        pre,promo,post=self.fixture();s={d:100 for d in pre};s.update({d:150 for d in promo});s.update({d:90 for d in post})
        r=estimate(s,pre,promo,post);self.assertEqual(r['uplift_pct'],50);self.assertEqual(r['post_dip_pct'],-10);self.assertEqual(r['net_uplift_pct'],30)
    def test_b1_weekday_adjustment(self):
        pre,promo,post=self.fixture();promo=promo[:3];s={d:10*(d.weekday()+1) for d in pre+promo+post}
        self.assertEqual(estimate(s,pre,promo,post)['incremental_units'],0)
    def test_b2_removes_common_trend(self):
        pre,promo,post=self.fixture();s={d:100 for d in pre};s.update({d:170 for d in promo});s.update({d:110 for d in post});c={d:200 for d in pre};c.update({d:240 for d in promo+post})
        r=estimate(s,pre,promo,post,[c],'B2');self.assertEqual(r['baseline_units'],840);self.assertEqual(r['uplift_pct'],Fraction(125,3));self.assertEqual(r['post_dip_pct'],Fraction(-25,3))
    def test_b2_control_zero_and_absence(self):
        pre,promo,post=self.fixture();s={d:1 for d in pre+promo+post};self.assertEqual(estimate(s,pre,promo,post,[],'B2')['reason'],'no_clean_control');self.assertEqual(estimate(s,pre,promo,post,[dict.fromkeys(s,0)],'B2')['reason'],'zero_control_baseline')
    def test_zero_treated_and_missing_window(self):
        pre,promo,post=self.fixture();s=dict.fromkeys(pre+promo+post,0);self.assertEqual(estimate(s,pre,promo,post)['reason'],'zero_treated_baseline');del s[post[-1]];self.assertEqual(estimate(s,pre,promo,post)['reason'],'incomplete_window')
    def test_negative_did_baseline(self):
        pre,promo,post=self.fixture();s={d:1 if d.weekday()==0 else 100 for d in pre+promo+post};c={d:100 for d in pre};c.update({d:0 for d in promo+post});self.assertEqual(estimate(s,pre,promo,post,[c],'B2')['reason'],'negative_daily_baseline')
    def test_complete_promotion_coverage(self):
        self.assertEqual(len(self.rows),480);self.assertEqual(len({r['promo_id'] for r in self.rows}),240)
        self.assertEqual(sum(r['status']=='available' and r['method']=='B1' for r in self.rows),240)
        self.assertTrue(all(r['reason']=='no_clean_control' for r in self.rows if r['method']=='B2'))
    def test_weighted_summary_and_null(self):
        groups=summarize(self.rows)
        for group in groups:
            valid=[r for r in self.rows if r['method']==group['method'] and r['customer_id']==group['customer_id'] and r['category']==group['category'] and (group['cohort']=='all' or not r['censored']) and r['status']=='available']
            self.assertEqual(group['available_promotions'],len(valid))
            if not valid:self.assertIsNone(group['uplift_pct'])
            else:self.assertEqual(group['baseline_units'],sum(r['baseline_units'] for r in valid))
    def test_validation_separate_and_counts(self):
        errors,summary=evaluate(ROOT/'data',self.rows);self.assertEqual(len(errors),240)
        self.assertTrue(all(r['uplift_mae_pp'] is None for r in summary if r['method']=='B2'))
        self.assertFalse(any('true_uplift_pct' in r for r in self.rows))
    def test_future_observations_do_not_enter(self):
        # Explicit cutoff makes every default promotion unavailable when its complete window lies in the future.
        early=build(ROOT/'data',dt.date(2024,1,31));self.assertTrue(all(r['reason']=='incomplete_window' for r in early))
    def test_exports_and_script_escaping(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder);errors,summary=evaluate(ROOT/'data',self.rows);export(self.rows,errors,summary,output)
            self.assertEqual(len(json.loads((output/'promotion.json').read_text())['estimates']),480)
            source=output/'evil.json';source.write_text('{"value":"</script><script>bad()</script>"}');target=output/'page.html';render(source,ROOT/'dashboard/m4.html',target)
            self.assertNotIn('</script><script>bad()',target.read_text());self.assertIn('\\u003c',target.read_text())
    def test_observed_estimator_boundary(self):
        source=(ROOT/'src/fmcg/uplift/estimators.py').read_text();self.assertNotIn('truth',source);self.assertNotIn('promotion_validation',source)

if __name__=='__main__':unittest.main()
