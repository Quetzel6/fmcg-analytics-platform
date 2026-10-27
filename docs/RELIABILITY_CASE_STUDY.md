# Sales correction and recovery: synthetic stakeholder brief

The fictional commercial manager and sales-operations analyst need a trustworthy
Jan–Sep 2026 Sale-In report before discussing the Q4 gap and promotion plan. They
need to know whether a revised total reflects changed prices or a duplicated load,
and whether yesterday's published report survives a failed refresh.

The chosen KPI is **P01 Sale-In amount, all retailers, Jan 1–Sep 30, 2026**.
It is the sum of delivered quantity × invoice unit price in integer satang, recognised
on delivered_date. Undelivered lines contribute zero. Display THB = satang / 100.
Source grain is order_id + line_id, with store and SKU; the existing report grain is
customer × SKU × sales type × YTD. Products, stores/customers and dates join through
the existing dimensions. The existing M2 SQL view and Python report define the KPI.

Everything is synthetic, including the business request and correction. Sale-In is
retailer delivery revenue in this simulation; it is not consumer Sale-Out or profit.
This case does not estimate promotional causality. Targets remain the authored
planning targets; historical corrections are not used to manufacture attainment.

## Reused behavior and the small addition

| Existing implementation | Reuse |
| --- | --- |
| `src/fmcg/generate.py` | Generate a fresh synthetic baseline in this run's directory |
| `src/fmcg/validate.py` | Full snapshot DQ gate, price/amount checks and manifest checks |
| `src/fmcg/load.py` | Atomic schema replacement, advisory lock, COPY and pre-commit reconciliation |
| `src/fmcg/analytics/metrics.py` | Existing `build`/`export` KPI calculation and report CSV/JSON |
| `sql/m2_views.sql` | Existing `v_m2_sku_ytd` SQL calculation, checked against the local report |
| `tests/test_m1.py`, `tests/test_m2.py` | Existing repeat/rollback and SQL/report parity test patterns |
| `scripts/run_release.py` | Existing stage-status/log convention; this demo retains a small run-specific record instead of replacing the release runner |

`scripts/case_study.py` orchestrates fixtures and existing functions. It adds one
UUID directory per run, timestamps, duration, stage outcomes, input/source/evidence
hashes and existing loader reports. It introduces no ingestion service or metric
formula. The Git base commit and file hashes together identify uncommitted work.

## Authored correction

The fictional source owner reports that P01's 2026 invoice price was understated
by 100 satang (THB 1) per unit. `correct_price` creates a separate revised snapshot:
update that price version and recalculate affected order-line unit prices/amounts.
Delivered quantities, order keys, inventory, Sale-Out and targets are unchanged.
Open lines retain zero amount. The expected YTD increase is delivered P01 units in
2026 × 100 satang. This is a full-snapshot historical correction, not incremental
upsert, CDC or time-travel storage.

The original fixture and manifest are retained. The revised manifest explicitly
records the parent manifest hash and authored correction; its file hashes/totals
are regenerated because this is a deliberately authored synthetic source revision.
Never repair checksums to make untrusted or corrupted incoming data pass. The
invalid fixture deliberately violates amount identity and retains its old manifest:
the DQ gate must reject it.

## Run it

From the repo root with Python dependencies installed and a disposable PostgreSQL
16 server running, set `FMCG_CASE_ADMIN_URL` to a database administrator connection
with CREATE DATABASE permission. Keep credentials in the process environment.
The script creates and drops only `fmcg_case_<run UUID>`; it never loads into the
admin URL's database. The current cloud development service uses:

```bash
cd /workspace/fmcg-analytics-platform
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
export FMCG_CASE_ADMIN_URL=postgresql://fmcg_dev@127.0.0.1:55432/fmcg_dev
python scripts/case_study.py
python -m unittest discover -s scripts -p 'test_case_study.py' -v
```

On Mac, use your existing dedicated local PostgreSQL connection instead; the
cloud port and role above are environment-specific. Each invocation creates a new
run directory and database. Tests execute a separate real demonstration and retain
its evidence in `output/case_study_tests/<run_id>/`. Without the admin variable the
five integration tests explicitly skip, which does not verify PostgreSQL.

## Follow the evidence and recover

The command prints `output/case_study/<run_id>/`. Read its `run.json` for the KPI
before/after/delta, actual UTC timestamps, base commit, source hashes and outcomes.
Each numbered stage JSON is the corresponding job record:

1. `01_baseline.json`: load the original snapshot and compare the SQL KPI with the
   existing Python report. `before/m2/` contains the report and exact evidence.
2. `02_dq_rejected.json`: expected `ValueError`. Inspect `rejected_quality.json`:
   DQ-06 identifies amount identity errors and DQ-16 identifies checksum/total
   mismatch. `dq_rejection.json` records the published database remaining at baseline. Recover by using the
   valid corrected source snapshot, not by editing DQ results.
3. `03_transaction_failed.json`: expected `InjectedFailure`, deliberately injected
   after real inserts and successful reconciliation but before commit, using the
   existing rollback-test technique. `in_transaction_reconciliation.json` shows
   revised totals inside the transaction. `rollback.json` shows the old published
   count/total/KPI after rollback. This is a controlled application failure, not a
   tested power-loss or network-outage scenario.
4. `04_recovery.json`: rerun the same loader with the valid corrected snapshot,
   without the injected fault. SQL and `corrected/m2/` must agree.
5. `05_repeat.json`: load the corrected snapshot again. Count, total and KPI must
   equal the recovery result; snapshot replacement must not append duplicates.

The two expected failures are deliberate demonstrations. Any unexpected failure
sets the overall run to failed and exits nonzero. Examine the last stage, its error
type and DQ/reconciliation evidence; fix the prerequisite and rerun the command for
a new linked-by-source demonstration. There is no resume-from-stage feature.
The temporary database is removed even after failure; fixtures and JSON evidence
remain. A cleanup failure marks the run failed and requires checking the run-owned
database on the local server. Process kills cannot guarantee cleanup.

Earlier candidate/ZIP evidence is historical after these source changes. The new
run verifies this case only; it does not recertify all M0–M5 outputs or remote CI.

## Five interview questions

1. **Why snapshot replacement? What is the alternative?** The existing loader
   supports an atomic complete snapshot with stable totals on rerun. Incremental
   upserts would require explicit change keys, deletions and late-arrival contracts;
   this case does not implement those. Full replacement costs more as data grows.
2. **How do you prove the corrected KPI is right?** Trace the 100-satang price
   revision to delivered units and line amounts, validate the new snapshot, compare
   the existing local M2 result and SQL view, and reconcile the exact delta.
3. **What happens when source data is wrong?** DQ fails before connecting/loading.
   The invalid fixture demonstrates amount and checksum failures. Correct the source
   revision and rerun; retain the rejected input and reasons as evidence.
4. **What if loading fails after inserting rows?** COPY, views and reconciliation
   share one transaction. The injected failure occurs before commit; a new connection
   sees the prior published KPI and totals. Recovery repeats the valid snapshot.
5. **How do you know the rerun did not duplicate sales?** Compare recovery/repeat
   row counts, full SI total and the selected KPI; the regression checks enforce
   equality. Hashes identify inputs/code but are not proof of real business accuracy.
