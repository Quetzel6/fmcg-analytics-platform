import copy
import datetime as dt
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fmcg.generate import ROOT
from fmcg.forecast.baselines import Series,METHODS,ORIGINS,load_series,predict,score,select_method,build,export

class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series=load_series(ROOT/'data'); cls.report=build(ROOT/'data')
    def test_backtest_protocol_complete_and_future_horizon(self):
        self.assertEqual(len(self.report['backtest_scores']),6)
        for score in self.report['backtest_scores']: self.assertEqual(score['points'],36); self.assertEqual(score['status'],'complete'); self.assertEqual(score['missing_predictions'],0)
        self.assertEqual(len(self.report['backtest_points']),216); self.assertEqual(len(self.report['forecasts']),108)
        self.assertEqual({r['month'] for r in self.report['forecasts']},{10,11,12}); self.assertEqual({r['year'] for r in self.report['forecasts']},{2026})
    def test_all_baselines_ignore_mutated_future_actuals(self):
        for origin in ORIGINS:
            changed=copy.deepcopy(self.series)
            for key in changed.amounts:
                if key[:2]>(origin.year,origin.month): changed.amounts[key]=10**25
            for method in METHODS: self.assertEqual(predict(self.series,origin,method),predict(changed,origin,method))
    def test_training_does_not_need_evaluation_data(self):
        for origin in ORIGINS:
            truncated=copy.deepcopy(self.series); truncated.end=origin; truncated.amounts={k:v for k,v in truncated.amounts.items() if k[:2]<=(origin.year,origin.month)}
            for method in METHODS: self.assertEqual(predict(self.series,origin,method),predict(truncated,origin,method))
    def test_known_constant_series_and_run_rate_formula(self):
        origin=dt.date(2025,9,30); data={(year,m,'A','Coffee'):100 if year==2024 else 200 for year in (2024,2025) for m in range(1,13)}
        series=Series(data,[dict(customer_id='A',customer_name='A')],['Coffee'],dt.date(2024,1,1),dt.date(2025,12,31))
        for method,expected in [('seasonal_naive',100),('ly_ytd_growth',200),('seasonal_run_rate',200)]: self.assertTrue(all(r['forecast_satang']==expected for r in predict(series,origin,method)))
        # Unequal prior seasonal indices: trailing actual / index yields a stable monthly run rate.
        for month in range(1,13): series.amounts[2024,month,'A','Coffee']=month*100
        for month in (7,8,9): series.amounts[2025,month,'A','Coffee']=month*200
        forecast=predict(series,origin,'seasonal_run_rate'); self.assertEqual([r['forecast_satang'] for r in forecast],[2000,2200,2400])
    def test_zero_and_missing_history_do_not_fabricate_rates(self):
        series=copy.deepcopy(self.series); origin=ORIGINS[0]
        for key in series.amounts:
            if key[0]==2024: series.amounts[key]=0
        for method in ('ly_ytd_growth','seasonal_run_rate'):
            predictions=predict(series,origin,method); self.assertTrue(all(r['forecast_satang'] is None for r in predictions)); _,metrics=score(predictions,series); self.assertIsNone(metrics['wape']); self.assertEqual(metrics['missing_predictions'],36)
        self.assertTrue(all(r['forecast_satang']==0 for r in predict(series,origin,'seasonal_naive')))
        missing=copy.deepcopy(self.series); del missing.amounts[2024,10,'C01','Coffee']; p=predict(missing,origin,'seasonal_naive'); self.assertEqual(next(r for r in p if r['customer_id']=='C01' and r['category']=='Coffee' and r['month']==10)['status'],'missing_ly_month')
    def test_wape_bias_known_values_and_zero_actual_denominator(self):
        series=Series({(2025,10,'A','Coffee'):100,(2025,11,'A','Coffee'):200},[],[],dt.date(2024,1,1),dt.date(2025,12,31))
        predictions=[dict(year=2025,month=month,customer_id='A',category='Coffee',forecast_satang=Fraction(value),method='seasonal_naive',origin='2025-09-30') for month,value in [(10,110),(11,160)]]
        _,metrics=score(predictions,series); self.assertEqual(metrics['wape'],Fraction(1,6)); self.assertEqual(metrics['bias'],Fraction(-1,10))
        series.amounts={k:0 for k in series.amounts}; _,metrics=score(predictions,series); self.assertIsNone(metrics['wape']); self.assertEqual(metrics['status'],'zero_actual_denominator')
    def test_selection_requires_strict_win_at_both_origins(self):
        scores=[dict(origin=o.isoformat(),method=m,wape=Fraction(20 if m=='seasonal_naive' else 10,100)) for o in ORIGINS for m in METHODS]
        self.assertEqual(select_method(scores)['selected_method'],'ly_ytd_growth')
        for r in scores:
            if r['origin']==ORIGINS[1].isoformat() and r['method']!='seasonal_naive': r['wape']=Fraction(20,100)
        self.assertEqual(select_method(scores)['selected_method'],'seasonal_naive')
    def test_outlook_and_gap_exact_reconciliation(self):
        selected=self.report['selection']['selected_method']
        for row in self.report['outlook']:
            remaining=sum(r['forecast_satang'] for r in self.report['forecasts'] if r['method']==selected and r['customer_id']==row['customer_id'] and r['category']==row['category'])
            self.assertEqual(row['forecast_remaining_satang'],remaining); self.assertEqual(row['full_year_outlook_satang'],row['actual_ytd_satang']+remaining); self.assertEqual(row['gap_to_annual_target_satang'],row['annual_target_satang']-row['full_year_outlook_satang'])
    def test_customer_and_global_outlook_summaries_reconcile(self):
        for summary in self.report['outlook_summary']:
            rows=[r for r in self.report['outlook'] if summary['customer_id']=='ALL' or r['customer_id']==summary['customer_id']]
            for field in ('actual_ytd_satang','forecast_remaining_satang','full_year_outlook_satang','annual_target_satang','gap_to_annual_target_satang'):
                self.assertEqual(summary[field],sum(r[field] for r in rows))
    def test_prediction_origin_and_unknown_method_validation(self):
        with self.assertRaises(ValueError): predict(self.series,dt.date(2025,9,15),'seasonal_naive')
        with self.assertRaises(ValueError): predict(self.series,dt.date(2027,9,30),'seasonal_naive')
        with self.assertRaises(ValueError): predict(self.series,ORIGINS[0],'invented_model')
        with self.assertRaises(ValueError): predict(self.series,ORIGINS[0],'seasonal_naive',6)
    def test_export_retains_repeating_rationals(self):
        with tempfile.TemporaryDirectory() as temp:
            export(self.report,Path(temp)); report=json.loads((Path(temp)/'forecast.json').read_text()); evidence=json.loads((Path(temp)/'rational_exact.json').read_text())
            self.assertEqual(report['data_class'],'100% SYNTHETIC'); self.assertEqual(len(evidence['forecasts']),108); self.assertIsInstance(report['selection']['comparisons'][0]['beats_naive_at_both_origins'],bool)
            first=evidence['forecasts'][0]['forecast_satang']; self.assertEqual(Fraction(int(first['numerator']),int(first['denominator'])),self.report['forecasts'][0]['forecast_satang'])
    def test_dashboard_escapes_embedded_markup(self):
        from fmcg.forecast_dashboard import render
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp); export(self.report,output); payload=json.loads((output/'forecast.json').read_text()); payload['data_class']='</script><script>alert(1)</script>'; (output/'forecast.json').write_text(json.dumps(payload)); self.assertNotIn('</script><script>alert',render(output).read_text())
    def test_forecast_sources_do_not_reference_private_inputs(self):
        for path in (ROOT/'src/fmcg/forecast').rglob('*.py'): self.assertNotIn('truth',path.read_text().lower())

if __name__=='__main__': unittest.main()
