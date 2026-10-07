# Authored Q4 Sale-In bridge: v1

This is an incremental scenario ledger over the unchanged default M3 forecast. It is stacked on PR #4 (receipt benchmark), whose CI passed. It does not establish improved forecasting accuracy, causal promotion incrementality or guaranteed target closure.

## Run

From the source root with the working Python environment active:

```bash
python -u scripts/run_release.py --local
export PYTHONPATH="$PWD/src"
python -m fmcg.q4_plan
open output/scenarios/q4-plan-v1/benchmark.html
```

Rebuild the default release first after switching branches so its manifest matches the current generator source. The planning command requires the default strict DQ gate to pass. It does not regenerate or change default data, M3 reports or targets. Outputs go to `output/scenarios/q4-plan-v1/`.

CI runs the default real-PostgreSQL release and all three supplemental commands before retaining output artifacts. The main release status describes the default acceptance; supplemental `planning_status.json` describes this authored plan.

## Future calendar and assumptions

Four illustrative C02 promotions are authored in `config/q4_plan_v1.toml`:

| SKU | Promotion dates | Authored baseline SO units/day | Maximum order cases |
| --- | --- | ---: | ---: |
| P01 Gold Coffee Jar 200g | 2026-10-12–10-25 | 45 | 6 |
| P03 3-in-1 Coffee Sachet x20 | 2026-11-10–11-23 | 50 | 8 |
| P10 Potato Crisps 50g | 2026-11-25–12-04 | 100 | 6 |
| P08 Chocolate Wafer 30g | 2026-12-24–12-31 | 100 | 6 |

All use PRICE_DISCOUNT at an authored 20% discount. These daily baselines, capacities and the calendar are **assumptions**, not observed future data. The 20% descriptor is not passed into an estimated elasticity model: historical mixed-discount effects are assumed transferable. There is no funding, GP, VAT, ROI or margin forecast here.

Observed B1 gross and post-period rates are weighted by their respective historical baseline units for each retailer-SKU, using all available historical promotions. Count and stockout count are retained. These rates can confound trend, seasonality and censoring. No planted effect enters planning.

M3 already embeds historical promotion patterns indirectly. Only an assumed **25%** of the transferred effect is treated as incremental beyond that baseline. This exposes the double-counting assumption; it is not a measured de-promotion correction and cannot prove double-counting has been eliminated.

| Scenario | Effect multiplier | Delivery delay |
| --- | ---: | ---: |
| Conservative | 0.5 | 3 days |
| Central | 1.0 | 0 days |
| Optimistic | 1.5 | 0 days |

These are authored scenarios, not statistical confidence intervals. The labels do not guarantee ordered SI amounts in every possible plan because case rounding, spare stock and capacity can change their relationship.

## Incremental stock accounting

1. Aggregate observed 2026-09-30 closing stock by retailer-SKU. Reserve seven days of the authored daily baseline; only stock above that reserve is incremental slack.
2. Transfer the historical gross rate through the incremental share/multiplier during the promo and the historical post rate over 14 days afterward. Negative daily delta is bounded by the baseline demand.
3. Size one future incremental order per retailer-SKU for positive delta demand beyond slack. Round up to product case size, apply a two-case retail minimum and the plan's maximum case capacity. The order is placed seven days before the promotion; the expected receipt is promotion start plus the scenario delay.
4. The daily delta ledger adds assumed receipts before that day's extra consumption. Missed incremental consumption is not backfilled. Negative delta frees baseline consumption into stock slack.
5. Reconcile exactly: opening slack + incremental receipts + avoided baseline consumption − fulfilled positive incremental SO = closing delta stock.

Baseline replenishment is assumed to maintain its reserved stock. This is **not** a full absolute inventory simulation and does not assess whether baseline demand itself can be supplied. It aggregates stores at retailer-SKU level and does not guarantee store availability. Shared truck/DC capacity and outstanding baseline orders are not separately simulated.

Retail order minimums and capacities are authored constraints; descriptive import MOQ, FCL and import lead-time fields are not applied as store-replenishment constraints.

## Monetary bridge and spillover

Additional SI units are credited on expected delivery dates at invoice prices known as of 2026-09-30, held fixed for the planning horizon. SO discounts do not change these invoice prices. Q4 receipts add to the relevant customer/category/month M3 amount forecast. Receipts in Q1 do not close the 2026 target gap.

The December P08 post period runs through 2027-01-14, and its Q1 demand delta is retained. Closing delta stock includes the full post period, so additional SI may leave stock rather than convert immediately into consumer sales.

Raw money is satang; displayed THB divides by 100. Exact fractions and money remain in CSV/JSON evidence.

## Default-plan result

| Scenario | Additional Q4 SI (THB) | ALL remaining gap (THB) | C02 remaining gap (THB) |
| --- | ---: | ---: | ---: |
| Unchanged M3 baseline | 0.00 | 484,653.13 | 736,265.00 |
| Conservative | 13,630.92 | 471,022.21 | 722,634.08 |
| Central | 25,336.08 | 459,317.05 | 710,928.92 |
| Optimistic | 29,370.24 | 455,282.89 | 706,894.76 |

The illustrative plan does not close the annual target. No target or baseline forecast is adjusted to manufacture attainment. Additional SI can increase retailer stock despite unfulfilled extra SO, so the monetary gap must be reviewed together with capacity, unserved increments and residual stock.

## Evidence and validation

- `planning.json`: complete authored assumptions, unchanged baseline, promotion ledgers, monthly/annual bridge.
- `promotions.csv`: rates, baseline/incremental assumptions, stock, order/case/price constraints, unserved demand and Q1 spillover.
- `monthly.csv`: 108 rows across three scenarios; baseline SI + additional SI = scenario SI.
- `outlook.csv`: retailer/ALL annual gaps and reconciliation.
- `rational_exact.json`: exact numerator/denominator evidence.
- `planning_status.json`: complete-run status and input/plan hashes.
- `benchmark.html`: offline gap and stock/delivery review.

Ten targeted tests passed: zero effect, spare stock, case/MOQ rounding, capacity, delayed receipts, Q1 revenue exclusion, post-dip ledger, bounded negative demand, invalid calendar/duplicate SKU/delay and monthly/annual reconciliation. The existing source-boundary guard now includes the planning package. Fresh core/PostgreSQL results must be read from this PR's CI.

To claim improved SI forecast accuracy, a promotion-aware historical backtest must use only calendars/effects available at each origin. This plan supplies decision assumptions and accounting, not that backtest.
