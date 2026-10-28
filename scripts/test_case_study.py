"""Real PostgreSQL regression checks; enabled only with a dedicated admin URL."""
import csv
import json
import os
from pathlib import Path
import unittest
from case_study import run
from fmcg.generate import ROOT


@unittest.skipUnless(os.environ.get('FMCG_CASE_ADMIN_URL'),'Case-study PostgreSQL admin URL not supplied')
class CaseStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=run(os.environ['FMCG_CASE_ADMIN_URL'],ROOT/'output/case_study_tests')
        cls.result=json.loads((cls.output/'run.json').read_text())
        print('Case-study evidence: '+str(cls.output),flush=True)
    def read(self,name):
        return json.loads((self.output/name).read_text())
    def test_price_correction_matches_quantity_and_reports(self):
        k=self.result['kpi']
        self.assertEqual(k['after']-k['before'],k['corrected_delivered_units']*100)
        self.assertEqual((k['before'],k['after'],k['delta'],k['corrected_delivered_units']),
                         (716741760,720506160,3764400,37644))
        snapshots=[]
        for folder in ('before','corrected'):
            with (self.output/folder/'warehouse/fact_order_line.csv').open(newline='') as stream:
                rows=list(csv.DictReader(stream))
            keys={(r['order_id'],r['line_id']) for r in rows}
            self.assertEqual(len(keys),len(rows))
            selected=[r for r in rows if r['product_id']=='P01' and '2026-01-01'<=r['delivered_date']<='2026-09-30']
            self.assertEqual(sum(int(r['delivered_qty']) for r in selected),37644)
            self.assertEqual(sum(int(r['amount_satang']) for r in selected),k['before' if folder=='before' else 'after'])
            snapshots.append([(r['order_id'],r['line_id'],r['delivered_date'],r['delivered_qty']) for r in rows])
        self.assertEqual(snapshots[0],snapshots[1])
        for folder,expected in [('before',k['before']),('corrected',k['after'])]:
            report=self.read(folder+'/m2/analytics.json')
            amount=sum(int(r['ty_amount_satang']) for r in report['sku_ytd'] if r['product_id']=='P01' and r['sales_type']=='SI')
            self.assertEqual(amount,expected)
    def test_dq_rejects_corrupted_amount(self):
        self.assertEqual(self.read('02_dq_rejected.json')['status'],'expected_failure')
        q=self.read('rejected_quality.json')
        self.assertEqual(q['status'],'failed')
        state=self.read('dq_rejection.json')
        self.assertEqual(state['before'],state['after'])
        for code in ('DQ-06','DQ-16'):
            self.assertGreater(next(r['count'] for r in q['rules'] if r['id']==code),0)
    def test_rollback_after_real_inserts_and_reconciliation(self):
        self.assertEqual(self.read('03_transaction_failed.json')['error_type'],'InjectedFailure')
        rollback=self.read('rollback.json')
        self.assertEqual(rollback['before'],rollback['after'])
        inside=self.read('in_transaction_reconciliation.json')
        self.assertEqual(int(inside['amount_totals_satang']['fact_order_line']),rollback['before']['all_si_satang']+self.result['kpi']['delta'])
    def test_recovery_and_repeat_preserve_counts_and_correct_kpi(self):
        recovered=self.read('04_recovery.json')['evidence']['database']
        repeated=self.read('05_repeat.json')['evidence']['database']
        before=self.read('01_baseline.json')['evidence']['database']
        self.assertEqual(recovered,repeated)
        self.assertEqual(recovered['order_lines'],before['order_lines'])
        self.assertEqual(recovered['p01_ytd_si_satang'],self.result['kpi']['after'])
    def test_run_evidence_complete_and_database_cleaned_up(self):
        import psycopg
        self.assertEqual(self.result['status'],'passed')
        self.assertTrue(self.result['postgresql_verified'])
        self.assertEqual(self.result['cleanup'],'completed')
        self.assertEqual([r['status'] for r in self.result['stages']],['passed','expected_failure','expected_failure','passed','passed'])
        self.assertIn('scripts/case_study.py',self.result['source_files'])
        self.assertIn('rollback.json',self.result['evidence_files'])
        self.assertTrue(all(r['duration_seconds']>=0 for r in self.result['stages']))
        with psycopg.connect(os.environ['FMCG_CASE_ADMIN_URL']) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM pg_database WHERE datname=%s',('fmcg_case_'+self.result['run_id'],)).fetchone()[0],0)


if __name__=='__main__': unittest.main()
