# FMCG Commercial & Supply Chain Analytics Platform

M0–M5 local implementation, PostgreSQL integration acceptance pending based on the supplied `DATA_SPEC.md` and `KPI_DICTIONARY.md`, with review corrections in `docs/REVIEW_NOTES.md`.

**100% synthetic, config-authored scenario.** No real company, retailer, brand, transaction or company price file is used. As-of **2026-09-30**. This project validates engineering/analysis methods on simulated data; its figures are not business findings.

## What changed from the earlier ZIP

The monthly SQLite demo and its independently generated supply facts are replaced by a single daily simulation. Delivered order quantities become inventory receipts; consumer SO quantities become ledger sold quantities. SI is delivered quantity × invoice price on delivery date. All prices and raw amounts are integer satang. The earlier HTML dashboard is replaced with a new M2 dashboard built against this daily contract.

## Run on Mac

Use Python **3.11 or later** (the existing Python 3.13 installation is sufficient for the language requirements). Extract the ZIP, open Terminal in `fmcg-platform`, then:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
python3 -m fmcg.generate
python3 -m fmcg.validate --strict-sanity
python3 tests/run_all.py
```

Generation and local validation need NumPy; PostgreSQL loading additionally uses psycopg. NumPy is pinned to 2.3.5; using another version fails config validation rather than silently changing random-stream checksums. Tests and generation were run in this execution environment, not on the user's Mac. No Docker is needed for local generation/QA.

`generate` replaces authored files in the chosen output folder; `data/` is a disposable generated scenario. Do not put original business files there. Change the seed/parameters in `config/scenario.toml` and regenerate to create a different scenario.

## Output and verification evidence

| Table | Grain | Rows in the default scenario |
| --- | --- | ---: |
| dim_date | Date | 1,004 |
| dim_customer | Fictional retailer | 3 |
| dim_store | Store | 15 |
| dim_product | SKU | 10 |
| dim_price | SKU/year | 30 |
| dim_promotion | Retailer-SKU window | 240 |
| fact_sales_daily | Date/store/SKU | 150,600 |
| fact_inventory_daily | Date/store/SKU | 150,600 |
| fact_order_line | Order/line | See manifest |
| fact_target_monthly | Month/customer/category, 2025–2026 | 288 |
| truth_demand_daily | Date/store/SKU | 150,600 |
| truth_promo_effect | Promotion | 240 |
| truth_supply_disruption | Disruption event | 24 |

Counts come from `data/manifest.json` and are tested against the default config. The panel count is 1,004 × 15 × 10. QA rules/definitions: `docs/DATA_SPEC.md`, `docs/KPI_DICTIONARY.md`. `output/data_quality.json` includes all rule results and scenario sanity measurements; these are validation diagnostics, not implemented M2/M5 business KPIs. `output/all_test_results.txt` and `output/test_summary.json` record the completed checks for this release.

Manifest includes config and generator hashes, seed, PCG64, NumPy version, each CSV's SHA-256/count and exact raw amount totals. The reproducibility test regenerates all files and compares the complete manifest, and checks that a changed seed produces different sales data.

## PostgreSQL setup and loading

Requires working Docker Compose on the user's machine:

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD and DATABASE_URL in .env to match.
set -a
source .env
set +a
docker compose up -d --wait
python3 -m fmcg.load
```

Use a dedicated local project database. The loader replaces **both `fmcg` and `truth` schemas**, including their objects/grants, in a single transaction. It acquires a transaction advisory lock, validates CSVs before connecting, COPY-loads every table, then checks row counts, NUMERIC amount totals and cross-table ledger reconciliations before committing. Any exception before commit rolls back schema replacement and inserted rows. `output/load_report.json` is produced only by running the loader; this ZIP does not invent a successful database report.

The observed date dimension ends at as-of. Future promises and 2026 Q4 target months are allowed planning dates, not future actuals. Credentials stay in `.env`/environment and are excluded from Git.

## PostgreSQL integration acceptance

Use a disposable dedicated database; this test replaces both project schemas:

```bash
export FMCG_TEST_DATABASE_URL="$DATABASE_URL"
python3 tests/run_all.py
```

The integration test runs a repeated load and injects a failure after insertions to test rollback. Without the database URL it is explicitly skipped. This environment has no PostgreSQL/Docker server, so database integration has not been executed. M1 cannot be marked fully accepted until this test passes.

## Architecture and next work

`config/scenario.toml` → one PCG64 simulation → `data/warehouse/*.csv` + isolated `data/truth/*.csv` → manifest/DQ gate → PostgreSQL transaction and reconciliation.

Source: `src/fmcg/generate.py`, `validate.py`, `load.py`, `contracts.py`; schema: `sql/schema.sql`; tests: `tests/test_m1.py`. Original user drafts are preserved under `docs/source_specs/`; reviewed working copies and decisions live in `docs/`.

M2 now exports commercial/service KPIs and a new offline dashboard. PostgreSQL views are included but require the integration acceptance test before SQL parity can be claimed. M3 now evaluates seasonal naive and alternative baselines at **2025-09-30 → Q4 2025** and **2026-06-30 → Q3 2026**, each 36 customer-category-month points, and produces Q4 2026 SI forecasts and full-year outlook. M4 now exports observed promotion estimators with isolated planted-effect validation; M5 now exports fixed inventory/risk rules and validation. See `docs/IMPLEMENTATION_STATUS.md`.

No RFM, ROI, margin, upstream container scheduling, real-data forecasting accuracy claim or production-scale claim is included.

## Git

```bash
git init
git add .gitignore README.md requirements.txt compose.yaml .env.example config src sql tests docs dashboard scripts .github
git commit -m "Build synthetic FMCG M0-M5 analytics and acceptance pipeline"
```

Generated data/output and `.env` are excluded. No GitHub repository or upload has been performed.

## M2 reports and Dashboard

After generation and validation:

```bash
python3 -m fmcg.report
python3 -m fmcg.dashboard
open output/m2/dashboard.html
```

C01–C10 and S01–S07 are calculated locally from warehouse facts only. CSVs include monthly SKU amounts/units/ASP/YoY/MoM, YTD contribution/dense rank, category attainment, quarter comparisons and retailer/global service metrics. SI uses delivery dates, target attainment uses Jan–Sep target, and short shipments close without remaining backlog.

`analytics.json` uses decimal strings and integer strings to prevent JavaScript precision loss. Exact rational calculations are preserved in `rational_exact.json`; the price/volume bridge also has `price_volume_exact.json`. Decimal representations have 50-digit working precision; display rounds to two decimals. Money totals remain exact integer satang.

The Dashboard has Customer, SI/SO and Category filters, monthly LY/TY lines, SKU bars/table, category SI target attainment, due-cohort service and an SO price/volume bridge. Contribution/rank retain the customer/type denominator after a category filter; service uses the retailer cohort and is unaffected by category/type filters.

`sql/m2_views.sql` creates `v_m2_monthly`, `v_m2_sku_ytd`, `v_m2_category_ytd` and `v_m2_service` during `fmcg.load`. Their cutoff is the loaded observed date dimension maximum. Local quarter comparisons are exported to CSV; the SQL monthly view is the input for equivalent quarter aggregations. PostgreSQL view parity has an optional database test and remains unverified here.

See `output/all_test_results.txt` for the combined M1/M2 test run and `docs/M2_ACCEPTANCE.md` for coverage and remaining limitations.

The test runner isolates small M1/M2 batches in separate processes and fails if either suite is incomplete; it writes per-suite logs, a combined log and test_summary.json.

## M3 forecasts and closing plan

```bash
python3 -m fmcg.forecast_report
python3 -m fmcg.forecast_dashboard
open output/m3/dashboard.html
```

The three baseline candidates are seasonal naive, LY × YTD growth and seasonal index × trailing run rate. Each backtest uses exactly 36 points; both specified origins are reported, and a method qualifies only if it strictly beats naive WAPE at both. See `docs/M3_ACCEPTANCE.md` for formulas/edge cases and `docs/M3_BENCHMARK.md` for the default synthetic benchmark.

`output/m3/` contains point-level backtests, WAPE/Bias summaries, all candidate Oct–Dec forecasts, selected-method annual outlook and gap, exact rational evidence and an offline Dashboard. The M2 and M3 pages link to one another. The final forecast protocol expects the default 2026-09-30 as-of; changing dates requires a new explicit protocol.

## M4 promotion estimators

```bash
python3 -m fmcg.promotion_report
python3 -m fmcg.promotion_dashboard
open output/m4/dashboard.html
```

B1 weekday-adjusted pre-period and B2 scaled additive DiD compare Sell-Out effects over 28-day pre / promotion / 14-day post windows. Full promotion coverage, stockout cohorts, weighted retailer/category effects and validation-only Bias/MAE are exported. The default calendar provides **no clean B2 controls**; unavailable rows and reasons are retained. B1 calculates all 240 promotions. See `docs/M4_ACCEPTANCE.md` for formulas, assumptions and results.

**Currency correction:** raw `_satang` values are divided by 100 for baht. M3 ALL shortfall is **THB 484,653.13**; C02 is **THB 736,265.00**, and C03 surplus is **THB 260,372.00**. M4 does not directly multiply SO uplift into SI forecast. No Q4 2026 promotion plan is supplied; the scenario requirements and double-counting/stock timing assumptions are documented in `docs/M4_CLOSING_PLAN.md`.

The current runner covers M1–M5 in isolated source-fingerprinted batches. PostgreSQL tests use `FMCG_TEST_DATABASE_URL`; the loader separately uses `DATABASE_URL`. Current test counts and full logs are in `output/test_summary.json` and `output/all_test_results.txt`.

## M5 inventory and risk

```bash
python3 -m fmcg.risk_report
python3 -m fmcg.risk_dashboard
open output/m5/dashboard.html
```

S08–S11 report 28-day days of cover, observed closing-zero availability and configurable excess stock. R01–R04 compare weekday uncensored cover with naive cover < 7 using complete future labels only in validation. Policy is in `config/risk.toml`; formulas/coverage/benchmark are in `docs/M5_ACCEPTANCE.md`.

Held-out 2026 matched precision is **6.24%**, recall **92.30%**, PR-AUC **0.2341**. Alerts are broad screening flags; upcoming receipts are not modelled, and the small difference versus naive is not a strong detector claim. Lost units are estimates with explicit matched coverage and monthly error, not guaranteed recovered sales.

The daily risk CSV contains the full 150,600-day panel; Dashboard JSON contains compact summaries and the latest 150 store-SKUs. Four Dashboard filters cover retailer/category/status/month. Latest snapshot stays at as-of, and validation stays on its fixed cohort. `docs/NEXT_STEPS.md` records outstanding PostgreSQL acceptance and portfolio review work. M3's SI outlook remains unchanged.

## Open the combined demo and close DB acceptance

Open `output/index.html` after extracting the ZIP to enter the M2–M5 dashboards. Rebuild this entry page after reports change:

```bash
python3 scripts/build_demo.py
```

With the virtual environment active, requirements installed and Docker Desktop running:

```bash
python3 scripts/accept_postgres.py
```

This creates a run-owned disposable PostgreSQL container on a random localhost port, requires both integration tests to pass without skips, retains real load/reconciliation evidence and cleans up the temporary container. It does not use your existing database or Compose volume. See `docs/POSTGRES_ACCEPTANCE.md`. The bundled attempt is blocked because this environment has no Docker; DB acceptance remains pending. Eight offline orchestration tests passed separately; their mocks are not PostgreSQL verification.

For a 5–7 minute mentor/interview walkthrough, see `docs/DEMO_WALKTHROUGH.md`.

## Rebuild and CI

```bash
python3 scripts/run_release.py --local
```

One command regenerates the synthetic scenario, strict DQ, M2–M5 reports/Dashboards, Demo and complete tests. Local success retains the explicit database-pending status. `.github/workflows/acceptance.yml` supplies a disposable PostgreSQL service and requires zero skipped core tests before database certification. Acceptance CI for the Q4 ledger in PR #5 passed on GitHub. See `docs/CI_RELEASE.md`.

## Supplemental Q4 commercial review

The authored Q4 plan is available on the feature branch. PR #5 acceptance CI passed, including the default PostgreSQL release. The older bundled Docker attempt described above is historical evidence, not the current CI result.

```bash
python -u scripts/run_release.py --local
export PYTHONPATH="$PWD/src"
python -m fmcg.q4_plan
open output/scenarios/q4-plan-v1/cockpit.html
```

Choose scenario, retailer and category to review monthly SI and incremental order dates/quantities. The annual target bridge follows scenario and retailer; no monthly or category targets are invented. Orders and receipts are authored assumptions. See [Q4 ledger assumptions](docs/Q4_PLAN_V1.md) and [commercial review workflow](docs/Q4_COMMERCIAL_REVIEW.md). Outputs include `cockpit.html` and `actions.csv`, with the original ledger evidence retained.
