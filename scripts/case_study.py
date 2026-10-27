"""Reproducible synthetic price correction and loader recovery demonstration."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from fmcg.generate import ROOT, generate, sha256
from fmcg.analytics.metrics import build, export
from fmcg.contracts import csv_path
from fmcg.validate import validate
import fmcg.load as loader
from evidence import sources


class InjectedFailure(RuntimeError):
    pass


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def change_csv(path, transform):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream); fields=reader.fieldnames; rows=list(reader)
    for row in rows:
        transform(row)
    with path.open('w', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return rows


def correct_price(before, after):
    """Author a new synthetic snapshot; never amend evidence for an untrusted input."""
    shutil.copytree(before, after)
    def price(row):
        if row['product_id']=='P01' and row['effective_from']=='2026-01-01':
            row['invoice_price_satang']=str(int(row['invoice_price_satang'])+100)
    change_csv(csv_path(after,'dim_price'), price)
    changed=[]
    def order(row):
        recognition=row['delivered_date'] or row['order_date']
        if row['product_id']=='P01' and recognition.startswith('2026-'):
            old=int(row['amount_satang'])
            row['unit_price_satang']=str(int(row['unit_price_satang'])+100)
            row['amount_satang']=str(int(row['delivered_qty'])*int(row['unit_price_satang']))
            changed.append(dict(order_id=row['order_id'],line_id=row['line_id'],
                                delivered_qty=int(row['delivered_qty']),before_satang=old,
                                after_satang=int(row['amount_satang'])))
    orders=change_csv(csv_path(after,'fact_order_line'), order)
    manifest=json.loads((after/'manifest.json').read_text())
    for table in ('dim_price','fact_order_line'):
        manifest['files'][table]['sha256']=sha256(csv_path(after,table))
    manifest['amount_totals_satang']['fact_order_line']=sum(int(r['amount_satang']) for r in orders)
    manifest['fixture_revision']=dict(kind='authored_synthetic_price_correction',
        parent_manifest_sha256=sha256(before/'manifest.json'),product_id='P01',
        effective_from='2026-01-01',invoice_price_delta_satang=100)
    write_json(after/'manifest.json',manifest)
    return changed


def local_kpi(data, output):
    quality,_=validate(data,ROOT/'config/scenario.toml',strict_sanity=True)
    write_json(output/'quality.json',quality)
    if quality['status']!='passed':
        raise ValueError('Fixture DQ failed')
    report=build(data,dt.date(2026,9,30)); export(report,output/'m2')
    value=sum(r['ty_amount_satang'] for r in report['sku_ytd']
              if r['sales_type']=='SI' and r['product_id']=='P01')
    return value


def database_state(url):
    with psycopg.connect(url) as conn:
        raw=conn.execute("SELECT COUNT(*), SUM(amount_satang::numeric) FROM fmcg.fact_order_line").fetchone()
        kpi=conn.execute("SELECT SUM(ty_amount_satang) FROM fmcg.v_m2_sku_ytd WHERE product_id='P01' AND sales_type='SI'").fetchone()[0]
    return dict(order_lines=raw[0],all_si_satang=int(raw[1]),p01_ytd_si_satang=int(kpi))


def run(admin_url, output_root):
    run_id=uuid.uuid4().hex
    output=output_root/run_id; output.mkdir(parents=True)
    started=dt.datetime.now(dt.timezone.utc)
    source_inventory=sources(ROOT)
    result=dict(run_id=run_id,status='running',data_class='100% synthetic',
                started_utc=started.isoformat(),stages=[],source_files=source_inventory,
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_note='Hashes include uncommitted files; base commit alone does not identify this run.')
    write_json(output/'run.json',result)
    database='fmcg_case_'+run_id
    url=make_conninfo(admin_url,dbname=database)
    created=False
    def stage(name, action, expected_error=None):
        stamp=dt.datetime.now(dt.timezone.utc).isoformat(); tick=time.monotonic()
        record=dict(name=name,started_utc=stamp,status='running')
        try:
            value=action()
            if expected_error:
                raise AssertionError('Expected failure did not occur: '+name)
            record.update(status='passed',evidence=value)
        except Exception as error:
            record.update(status='expected_failure' if expected_error and isinstance(error,expected_error) else 'failed',error_type=type(error).__name__)
            if record['status']=='failed':
                raise
        finally:
            record['duration_seconds']=round(time.monotonic()-tick,3)
            result['stages'].append(record)
            write_json(output/(name+'.json'),record)
            write_json(output/'run.json',result)
        return record
    try:
        before=output/'before'; after=output/'corrected'
        generate(ROOT/'config/scenario.toml',before)
        changes=correct_price(before,after); write_json(output/'correction.json',changes)
        before_value=local_kpi(before,output/'before')
        after_value=local_kpi(after,output/'corrected')
        delta=sum(r['after_satang']-r['before_satang'] for r in changes)
        if after_value-before_value!=delta or delta<=0:
            raise AssertionError('Correction does not reconcile to report KPI')
        result['kpi']=dict(name='P01 Sale-In Jan–Sep 2026, all retailers',unit='satang',
                           before=before_value,after=after_value,delta=delta,
                           corrected_delivered_units=sum(r['delivered_qty'] for r in changes))
        with psycopg.connect(admin_url,autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        created=True
        def load_snapshot(data):
            report=loader.load(data,ROOT/'config/scenario.toml',url)
            state=database_state(url)
            expected=before_value if data==before else after_value
            if state['p01_ytd_si_satang']!=expected:
                raise AssertionError('SQL/report parity failed')
            return dict(database=state,load_report=report,input_manifest_sha256=sha256(data/'manifest.json'))
        baseline=stage('01_baseline',lambda:load_snapshot(before))['evidence']['database']
        invalid=output/'invalid'; shutil.copytree(after,invalid)
        def bad(row):
            if row['product_id']=='P01': row['amount_satang']=str(int(row['amount_satang'])+1)
        change_csv(csv_path(invalid,'fact_order_line'),bad)
        dq,_=validate(invalid,ROOT/'config/scenario.toml')
        write_json(output/'rejected_quality.json',dq)
        if dq['status']!='failed': raise AssertionError('Invalid fixture accepted')
        stage('02_dq_rejected',lambda:loader.load(invalid,ROOT/'config/scenario.toml',url),ValueError)
        rejected_state=database_state(url)
        if rejected_state!=baseline: raise AssertionError('DQ rejection changed published data')
        write_json(output/'dq_rejection.json',dict(before=baseline,after=rejected_state))
        original=loader.database_reconcile
        def fail_before_commit(conn,tables):
            report=original(conn,tables)
            write_json(output/'in_transaction_reconciliation.json',report)
            raise InjectedFailure('Synthetic failure after reconciliation, before commit')
        def fail():
            with patch.object(loader,'database_reconcile',fail_before_commit):
                loader.load(after,ROOT/'config/scenario.toml',url)
        stage('03_transaction_failed',fail,InjectedFailure)
        rolled_back=database_state(url)
        if rolled_back!=baseline: raise AssertionError('Rollback did not preserve published KPI/count/total')
        write_json(output/'rollback.json',dict(before=baseline,after=rolled_back))
        recovered=stage('04_recovery',lambda:load_snapshot(after))['evidence']['database']
        repeated=stage('05_repeat',lambda:load_snapshot(after))['evidence']['database']
        if recovered!=repeated or recovered['order_lines']!=baseline['order_lines']:
            raise AssertionError('Repeated load duplicated or changed totals')
        if sources(ROOT)!=source_inventory: raise AssertionError('Source changed during run')
        result.update(status='passed',postgresql_verified=True)
    except Exception as error:
        result.update(status='failed',error_type=type(error).__name__,postgresql_verified=False)
        raise
    finally:
        try:
            if created:
                with psycopg.connect(admin_url,autocommit=True) as conn:
                    conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
            result['cleanup']='completed'
        except Exception as error:
            result.update(status='failed',cleanup='failed',cleanup_error_type=type(error).__name__)
            raise
        finally:
            result['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
            result['duration_seconds']=(dt.datetime.now(dt.timezone.utc)-started).total_seconds()
            result['evidence_files']={p.relative_to(output).as_posix():sha256(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='run.json'}
            write_json(output/'run.json',result)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output/case_study')
    args=parser.parse_args()
    url=os.environ.get('FMCG_CASE_ADMIN_URL')
    if not url: parser.error('Set FMCG_CASE_ADMIN_URL for a disposable local PostgreSQL server with CREATE DATABASE permission')
    try:
        print(run(url,args.output))
    except Exception as error:
        raise SystemExit('Case study failed: '+type(error).__name__+'; inspect run.json (connection details omitted)')
