# KPI Dictionary

**Status:** Reviewed working dictionary v0.2. M2 C01–C10/S01–S07 are locally implemented and tested; PostgreSQL view parity is pending. M3 F01–F04/C11–C12 are locally implemented; M4–M5 are locally implemented; estimator and risk limitations are documented in their acceptance files. Companion to DATA_SPEC.md; original v0.1 preserved in source_specs/.
**Data class:** synthetic. KPIs demonstrate definitions, not real performance.

## 0. Conventions

| Topic | Rule |
|---|---|
| Money | Stored as integer satang. Baht = satang / 100 at presentation only. Aggregation uses `NUMERIC`, never floating point |
| Percentages | Stored unrounded; rounded only for display |
| Zero denominators | Return `NULL`, never 0% and never a fabricated rate |
| As-of date | 2026-09-30. Nothing after it may be used |
| Period comparison | "LY" means the same calendar months one year earlier. For YTD, both sides use the same month range |
| Leap-day caveat | Feb 2024 has 29 days vs 28 in 2025, a ≈3.6% day-count difference in that month. Monthly YoY ignores it; a daily-rate variant (amount ÷ days) removes it |
| Sale-In vs Sell-Out | Different price bases (invoice vs shelf). Compare **quantities** across SI and SO, not amounts |
| Basis | Targets and forecast are on **Sale-In amount**, recognised on `delivered_date` |
| Milestone | The milestone (M1–M5) in which the KPI is implemented and tested |

## 1. Commercial KPIs

| ID | KPI | Definition | Grain / filters | Source | Edge cases and notes | M |
|---|---|---|---|---|---|---|
| C01 | Sell-Out (SO) Qty / Amount | Σ `quantity`, Σ `amount_satang` | any slice of date, store, customer, SKU, category | `fact_sales_daily` | Zero rows are real zeros (panel is complete) | M2 |
| C02 | Sale-In (SI) Qty / Amount | Σ `delivered_qty`, Σ `amount_satang` by `delivered_date` | same | `fact_order_line` | Open lines have no delivery and contribute 0. Short shipments count only the delivered quantity | M2 |
| C03 | YoY growth % | (TY − LY) / LY × 100 | month, YTD, quarter | C01 / C02 | LY = 0 → NULL. Report amount and quantity growth separately | M2 |
| C04 | MoM growth % | (month − previous month) / previous month × 100 | month | C01 / C02 | Seasonality dominates; never present MoM alone as a trend | M2 |
| C05 | YTD | Σ from 1 Jan to the as-of month, same range for LY | customer, category, SKU | C01 / C02 | As-of is a month end, so ranges are whole months | M2 |
| C06 | Contribution % | SKU TY amount / Σ TY amount within the same customer and sales type × 100 | customer × sales type | C01 / C02 | Contributions sum to 100% per partition (tested) | M2 |
| C07 | SKU rank | `DENSE_RANK()` by TY amount descending within customer and sales type | customer × sales type | C01 / C02 | Ties share a rank | M2 |
| C08 | Average selling price (ASP) | Amount ÷ Quantity | any slice | C01 / C02 | Quantity 0 → NULL | M2 |
| C09 | Price / volume effect | Per SKU: volume effect = (Q_TY − Q_LY) × P_LY; price effect = (P_TY − P_LY) × Q_TY. Sum = ΔAmount | SKU, customer | C01 | Two-factor split is exact when both periods have positive quantity; otherwise NULL components plus an explicit undecomposed delta. When aggregated across SKUs, any mix change appears inside the volume effect; no separate mix term is reported | M2 |
| C10 | Target attainment % | YTD SI amount / YTD target × 100 | customer × category | C02, `fact_target_monthly` | Target is limited to the same months as the actuals. Never divide YTD actual by the annual target | M2 |
| C11 | Full-year outlook | YTD SI actual + forecast for the remaining months | customer × category | C02, F01 | A planning estimate, not a commitment | M3 |
| C12 | Gap to annual target | Annual target − full-year outlook | customer × category | C11 | Positive = shortfall, negative = expected overshoot | M3 |

## 2. Forecast KPIs

Forecast object: Sale-In amount, by customer × category × month, horizon Oct–Dec.

| ID | KPI | Definition | Notes | M |
|---|---|---|---|---|
| F01 | Forecast | Method output; candidates: (a) seasonal naive (LY same month), (b) LY × YTD growth factor, (c) seasonal index × trailing run-rate | A method may use only data on or before its origin date. The planned promotion calendar is **not** used in these baselines | M3 |
| F02 | WAPE | Σ\|A − F\| / Σ A | Σ over the evaluation set (36 points per origin: 3 customers × 4 categories × 3 months) | M3 |
| F03 | Bias | Σ(F − A) / Σ A | Positive = over-forecast | M3 |
| F04 | Backtest protocol | Origins 2025-09-30 (target Q4 2025) and 2026-06-30 (target Q3 2026); actuals from the same simulation | A method is described as better only if it beats seasonal naive (a) on both origins. Q3 is easier than Q4 because it has no festive peak; both results are reported | M3 |

## 3. Supply chain KPIs

Service metrics use the **due cohort**: lines with `promised_date ≤ as-of`. Lines promised later are pending and excluded.

| ID | KPI | Definition | Notes | M |
|---|---|---|---|---|
| S01 | Fill rate % | Σ `delivered_qty` / Σ `ordered_qty` over the due cohort × 100 | Late quantities count as delivered. This is not on-time fill rate | M2 |
| S02 | On-time rate % (line) | Due lines with `delivered_date ≤ promised_date` / due lines × 100 | Open overdue lines count as not on time | M2 |
| S03 | In-full rate % (line) | Due lines with `delivered_qty = ordered_qty` / due lines × 100 | Open lines are not in full | M2 |
| S04 | Line OTIF % | Due lines that are both on time and in full / due lines × 100 | | M2 |
| S05 | Order OTIF % | Orders in which every due line is OTIF / orders with ≥ 1 due line × 100 | Order and line rates use different weights; neither universally bounds the other. Lines of the same order that are not yet due are ignored; this is a due-cohort measure, not full-lifecycle compliance | M2 |
| S06 | Order lead time | `delivered_date − order_date` in days: mean and P90 | Delivered lines only | M2 |
| S07 | Backlog / overdue backlog | Σ(`ordered_qty` − `delivered_qty`) over open lines; overdue = lines with `promised_date ≤ as-of` | Short-shipped remainders are cancelled, not backlog | M2 |
| S08 | Days of cover | Closing stock ÷ mean daily `sold_qty` over the last 28 days | Zero-sale average → NULL. Sales are censored on stockout days, so cover is overstated for items that recently ran out | M5 |
| S09 | Stockout day (observed) | Store-SKU-day with `closing_qty = 0` | End-of-day observation; a proxy. Validated against `truth.lost_qty > 0` in M5 | M5 |
| S10 | Availability % | (1 − stockout days / store-SKU-days) × 100 | Observed proxy; compare with true availability from `truth` in validation only | M5 |
| S11 | Excess stock flag | Days of cover above a threshold (initial 60 days) | Threshold is configurable. No stock valuation (no cost data) | M5 |

## 4. Promotion KPIs (M4)

Promotion window = `start_date` to `end_date`. Pre-period = 28 days before start. Post-period = 14 days after end.

| ID | KPI | Definition | Notes |
|---|---|---|---|
| P01 | Baseline units | Counterfactual daily units without promotion. Two estimators compared: **B1** pre-period average, weekday-adjusted; **B2** difference-in-differences against the same SKU at retailers with no promotion in the same window | B2 controls for seasonality and trend that B1 ignores. No eligible control or zero control baseline → NULL with reason |
| P02 | Incremental units | Actual − baseline, summed over the promotion window | |
| P03 | Uplift % | Incremental units / baseline units × 100 | |
| P04 | Post-promo dip % | (Actual − baseline) over the post-period / baseline over the post-period × 100 | Expected negative (pull-forward) |
| P05 | Net uplift % | (Window incremental + post-period incremental) / window baseline × 100 | The honest total effect; uplift alone overstates |
| P06 | Estimator error | Estimated uplift − `truth.true_uplift_pct`: bias and MAE over all promotions, in percentage points | Validation only |
| P07 | Censoring flag | Promotion windows containing at least one observed stockout day | Sales are capped there, so uplift is biased low. Report results with and without flagged promotions |

Not computed: promotion ROI and margin (no cost or funding data).

## 5. Risk detection KPIs (M5)

The detector may use only data on or before day *t*.

| ID | KPI | Definition | Notes |
|---|---|---|---|
| R01 | OOS risk flag | Rule-based (and optionally model-based) flag that a store-SKU will stock out within 7 days, e.g. projected cover < expected lead time. Exact rule fixed and documented in M5 before evaluation | Never tuned on the evaluation period |
| R02 | Label | 1 if `truth.lost_qty > 0` on any day in (t, t+7] | Validation only |
| R03 | Precision / Recall / PR-AUC | Standard, flag vs label, over store-SKU-days after burn-in with the full 7-day future label window observed | Stockouts are rare (class imbalance), so accuracy is not reported. Compared with the naive rule "days of cover < 7" |
| R04 | Lost-sales estimate error | Estimated lost units vs `truth.lost_qty`, by month and category | Validation only |

## 6. Rules for citing a KPI

1. A KPI is documented as implemented only after its milestone is complete and its tests pass.
2. Any figure derived from planted effects (uplift, stockout detection) is described as "validated against known synthetic ground truth", never as a business finding.
3. The README states the data class, the as-of date and the definition link next to every headline number.

## 7. Review corrections (v0.2)

S05 has no universal inequality with S04; see the counterexample/test in REVIEW_NOTES.md. S07 excludes positive short deliveries because their remainders are cancelled. P06 validates planted demand multipliers, not noisy realised ratios; observed stock censoring is reported separately. M1 scenario metrics are QA diagnostics. Current M2 implementation evidence is in M2_ACCEPTANCE.md; M3 acceptance is recorded in M3_ACCEPTANCE.md; M4 implementation and estimator limitations are in M4_ACCEPTANCE.md; M5 implementation and fixed-rule limitations are in M5_ACCEPTANCE.md.
