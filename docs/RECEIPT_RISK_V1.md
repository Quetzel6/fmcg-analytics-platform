# Receipt-aware stock risk: fixed v1 benchmark

This is a supplemental screening experiment, not a replacement for M5 or automatic ordering. It builds on the staggered promotion branch (PR #3), whose CI passed; this PR is stacked on that branch.

## Run

With the working environment active at the source root:

```bash
export PYTHONPATH="$PWD/src"
python -m fmcg.receipt_scenario
open output/scenarios/receipts-v1/benchmark.html
```

Data is written only to `data/scenarios/receipts-v1/`; benchmark outputs go to `output/scenarios/receipts-v1/`. The existing default dataset, M3 forecast, M5 policy and 2026 results are not replaced. CI runs the default PostgreSQL-required release, staggered promotion benchmark and this receipt benchmark, retaining their outputs together.

## Fixed protocol before outcome inspection

- Separate synthetic seed: 20261008, observed simulation dates 2024-01-01 through 2027-09-30.
- Supplemental promo months: March/September in full years; March in the final year. This keeps the existing DQ promotion-count contract satisfied over the longer simulation.
- Reserved predictions: **2027-01-01 through 2027-09-23**. Labels require every day in the next seven-day observed window.
- Same 28-day weekday-uncensored daily demand estimate as M5.
- Expected receipt credit: exactly **4/5 of ordered units** on a promised date one to seven days after the snapshot.
- The v1 policy loader rejects changes to this fraction, method/windows or reserved period. A different rule requires a new protocol and unseen evaluation period.

The 2027 label cohort was generated for this experiment and was not used to tune the fraction or threshold. Once these results are inspected, this cohort is no longer unseen for subsequent tuning. These are simulated future dates, not observed real 2027 business records.

## As-of information and calculation

Only orders created on or before the snapshot can be considered. A line with a delivery already observed by the snapshot is closed, including short deliveries whose remainder is cancelled under the existing contract. A future delivery date is used only to establish that no receipt has yet been observed; it never sets the predicted arrival date. Actual future delivered quantity and future orders are not prediction inputs.

Open orders with overdue promises or promises beyond seven days receive no receipt credit. They remain visible in open/overdue diagnostics. Arrival assumptions can still be wrong: no carrier visibility, revised ETA, lead-time distribution or causal inventory response is modelled.

Start with observed closing stock. At each future day, add that day's credited receipts and subtract the past-only mean daily demand. Flag if any daily projected closing balance is negative. A receipt on day 3 cannot hide a shortage on day 2.

For minimum projected balance m and seven-day expected demand d, the ranking score is d/(2d+m). With no receipts this exactly equals the existing M5 score; score > 1/2 corresponds to a negative projected balance. Zero/unavailable mean demand remains unscored.

Observed features are completed before a separate validation module reads planted lost demand. The label is any positive lost quantity over days 1–7 after the snapshot; current-day losses are excluded. Both methods use exactly the same complete, scored observations.

## Observed result

Strict DQ-01–DQ-17: zero findings. Supplemental daily panel: 205,350 rows. Matched reserved cohort: 39,900 observations, with no unscored rows.

| Method | Precision | Recall | PR-AUC | False positives | False negatives |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing weekday-uncensored cover | 6.15% | 93.64% | 0.2112 | 30,513 | 136 |
| Promised receipt path v1 | 7.04% | 69.35% | 0.1852 | 19,565 | 655 |

False positives decrease by 10,948, but false negatives rise by 519 and ranking PR-AUC falls. This does **not** establish overall superiority. Keep the existing M5 rule as the current screening baseline; use the new page to explain the receipt assumption and its tradeoff. Precision remains low in both cases.

Results are not comparable numerically to the default 2026 benchmark because the new seed, period and calendar produce a different dataset. Compare methods within this 2027 matched cohort only.

## Evidence and tests

- `benchmark_status.json`: matched metrics, policy, scenario/generator/policy hashes.
- `data_quality.json`: all strict DQ findings.
- `risk_validation.csv`: full-precision counts and metrics.
- `latest_risk.csv`: as-of predictions only; latest snapshots lack complete future labels and are not evaluated.
- `benchmark.html`: offline comparison, with links to machine-readable evidence.

Ten targeted tests passed: no-receipt equivalence, expected receipt credit, shortages before later arrivals, future-created/received lines, overdue/outside-horizon exclusions, invariance to future actual delivery outcomes, unscored demand, frozen protocol validation, reserved complete labels and HTML output.

The 15 existing M5 regression tests also passed after rebuilding default M5 exports; the risk source boundary check passed. Supplemental manifest reproducibility is checked by repeated runs. Fresh complete core/PostgreSQL acceptance is delegated to this PR's CI and must be read from that run.

Next: evaluate revised ETA/reliability or new demand rules only on a separately reserved period, and define business costs for missed shortages versus false alerts before choosing an operating policy.
