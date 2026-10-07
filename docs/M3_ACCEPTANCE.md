# M3 forecast and closing-plan acceptance

Implemented: F01–F04 and C11–C12 on synthetic delivered Sale-In amounts. This protocol is fixed at as-of 2026-09-30 with an Oct–Dec 2026 closing horizon; a different final as-of is rejected rather than silently producing a partial full-year outlook.

## Models fixed before evaluation

A — `seasonal_naive`: forecast = observed SI of the same month one year before the forecast month.

B — `ly_ytd_growth`: forecast = LY same-month SI × (SI YTD current year / SI YTD prior year), using the same Jan–origin month range. Zero LY YTD means unavailable, not a fabricated factor.

C — `seasonal_run_rate`: prior full-year monthly index = that month's SI / (prior-year annual SI / 12). Divide each of the last three completed observed months by its prior-year month index; their mean is the deseasonalized run rate. Multiply that rate by the forecast month's index. Missing prior-year/trailing history or a zero trailing index makes the estimate unavailable. A zero forecast-month index gives a valid zero forecast. Indices are learned from historical SI amounts, never copied from scenario seasonality parameters.

All training dictionaries physically exclude months after origin. Inputs are delivered order amounts and retailer/product/store mappings; no planned promotion calendar or private validation data feeds prediction.

## Backtest protocol

| Origin | Evaluation horizon | Points per method |
| --- | --- | ---: |
| 2025-09-30 | Oct–Dec 2025 | 36 |
| 2026-06-30 | Jul–Sep 2026 | 36 |

Three retailers × four categories × three months = 36 points. Across three methods and two origins there are 216 auditable point records. WAPE = sum absolute errors / sum actuals; Bias = sum(forecast−actual) / sum actuals. Ratios are stored unrounded as rational working values, with exact numerator/denominator evidence; percentages are display-only scaling by 100.

A method with missing predictions is not scored on a smaller favorable subset. Scores are NULL/unavailable when any required prediction is missing or the actual denominator is zero. Missing evaluation actuals are an error.

## Selection rule

An alternative is eligible only if its WAPE is strictly lower than seasonal naive at **both** origins. If multiple qualify, use lowest mean WAPE across the two origins, with deterministic method-order tie-break. Otherwise retain seasonal naive. Bias is reported but does not change the fixed ranking criterion. Selection uses these historical synthetic evaluation windows; it is not an untouched prospective accuracy claim.

Default benchmark results appear in M3_BENCHMARK.md and the raw point/score CSVs. This scenario selected `ly_ytd_growth`.

## Closing plan

C11 = Jan–Sep 2026 delivered SI actual + selected Oct–Dec forecast.
C12 = full-year 2026 SI target − C11. Positive gap means shortfall; negative means projected overshoot. Targets remain planner inputs fixed from LY, not inferred from the forecast. These are planning estimates, not confirmed orders or a commitment.

Exports: `backtest_points.csv`, `backtest_scores.csv`, `forecasts.csv` (all three final-origin candidates), `outlook.csv` (selected method, retailer/category), `outlook_summary.csv` (retailer/global), `forecast.json`, `rational_exact.json`, and `dashboard.html`. Predictions remain fractional satang estimates, without premature rounding; actual/target source amounts are integer satang.

Dashboard filters retailer and comparison method. The comparison selector affects only the candidate forecast table; validated-method outlook/cards retain the selected method. Backtest scores always show all-retailer evaluation. Both boundaries are labelled.

## Tests and limits

Tests mutate every future amount after each origin and confirm identical predictions; truncated history produces the same forecasts. Hand-calculated constant/seasonal fixtures verify each formula, WAPE/Bias and strict selection rules. Zero/missing history, point counts, exact outlook/gap, summary reconciliation, origin validation, rational exports and embedded-script escaping are tested. Source guards reject private-input references in forecast modules. The actual Dashboard script and both filters were exercised with a DOM harness.

PostgreSQL integration remains pending from M1/M2; M3 is a local CSV-based forecast engine. No model accuracy on real data, demand forecast, promotion causality, or production scaling claim is made. M4/M5 are still future work.

Release verification: 13 M3 cases passed; complete M0–M3 checks: 47 passed, 2 PostgreSQL cases skipped. Batch logs and fingerprints are retained in output/checks/.
