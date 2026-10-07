# M5 inventory and stockout risk

Locally implements S08–S11 and R01–R04 for the synthetic daily warehouse. PostgreSQL repeat-load/rollback and M2 SQL parity acceptance remain pending. No risk model is deployed and no replenishment orders are written.

## Fixed protocol and leakage boundary

`config/risk.toml` was authored before evaluation. History is fixed at 28 days, horizon at 7 days, held-out cohort starts 2026-01-01 and excess threshold defaults to 60 days. The threshold is configurable; window/horizon and method changes require a new explicit protocol. No label-based tuning or model selection is performed. Descriptive import lead times are not used as retail store delivery lead times.

Features at close of day t use only observed inventory on or before t. S08 daily mean sold is over [t−27,t], including zeros. Cover = closing / mean; zero means and incomplete windows give NULL. S09 observed stockout is closing = 0. S10 observed availability is nonzero-closing store-SKU-days / all store-SKU-days × 100. S11 excess is cover > configured threshold; unknown cover produces an unknown flag, not false.

R01 `weekday_uncensored_cover` computes seven weekday means from the same trailing window, retaining only days with closing > 0. Average these weekday means to obtain daily demand; a missing weekday or zero demand yields an unavailable score. Adjusted cover = closing / adjusted daily demand; flag iff cover < 7, strictly. Ranking score = 7 × demand / (closing + 7 × demand); it is a monotonic cover score, **not a calibrated probability**. The naive comparator uses the all-day sold mean and the same cover < 7 threshold. Scores and flags are exact Fractions/booleans; CSV/JSON decimal strings use 50-digit precision. Display rounds values.

The rules do not anticipate incoming receipts, planned promotions or capacity constraints. Ordinary replenishment therefore creates many false positive alerts even when cover is low. Filtering observed stockout days also changes the sample and can bias demand upward; unobserved intraday censoring can remain on days with positive closing stock. These are screening rules, not an automatic order policy or causal demand recovery model.

## Validation-only labels and metrics

Only `risk_validation.py`, outside the risk directory, reads private demand. R02 label is any lost_qty > 0 in **(t,t+7]**, excluding current day. Both warehouse rows and labels must contain every future day; no window is shortened or padded. For the default period, eligible origins are 2024-01-28 through 2026-09-23. Latest 2026-09-30 scores are operational snapshots without a complete future label and are excluded from evaluation.

R03 reports all eligible rows and held-out 2026 rows, each method's individual coverage, and matched cohorts where both scores exist. Precision = TP/(TP+FP); recall = TP/(TP+FN). Undefined denominators remain NULL. PR-AUC is the trapezoidal integral of grouped-score precision/recall, starting at (recall 0, precision 1). Average precision is separately exported as the step-integral; ties are processed together. Neither metric is reported when no positive labels exist. No accuracy metric is used. Overlapping seven-day windows are dependent; point counts are not independent experimental observations and no significance claim is made.

## Lost sales and proxy availability

For R04, same-day estimated lost units are max(prior matching-weekday mean − observed sold, 0) when closing = 0; the mean uses nonzero-closing days in **[t−28,t−1]**, excluding t. After complete prior history, positive-closing days receive estimate zero. A closing-zero day with no eligible matching weekday is NULL. Estimates ignore promotion demand changes and may understate loss during spikes. No margin, revenue recovery or stock valuation is inferred.

Monthly retailer/category validation reports estimated days, missing days, actual lost units on matched days and actual lost units on all days. Aggregate error is sum estimates − sum matched actual; daily MAE and daily WAPE separately avoid hiding cancellation of positive/negative errors. Full-history availability validation compares the closing-zero proxy with same-day positive lost demand; it does not leak labels into prediction features.

## Default benchmark

Held-out 2026 matched cohort: **39,893 scored store-SKU-days**, 2,118 positive labels; 7 of 39,900 eligible origins are unavailable. Positive prevalence is 5.31%.

| Method | Precision | Recall | PR-AUC | AP |
| --- | ---: | ---: | ---: | ---: |
| Weekday uncensored cover | 6.24% | 92.30% | 0.2341 | 0.2016 |
| Naive cover < 7 | 6.23% | 91.45% | 0.2324 | 0.1999 |

The fixed alternative catches 18 additional positives but adds 199 false positives on the matched sample (29,361 vs 29,162). The difference is small and does not justify a claim of a strong operational detector. Keep both methods visible. Any new receipt-aware rule needs a newly reserved evaluation period before tuning; do not optimise the exposed held-out labels.

Across all 150,600 observed days, closing-zero days = 2,391 and lost-demand days = 2,246. Observed availability is 98.4124% vs actual synthetic availability 98.5086%; the proxy has 145 false positives and 0 false negatives in this particular scenario. This is validation against known synthetic ground truth, not evidence about real retailer availability.

2026 matched lost units: estimated 3,802.75 versus actual 4,456, aggregate error −653.25 units. The full export also includes daily errors by month/category/retailer. Latest snapshot: 150 store-SKUs, 120 rule flags, no excess flags at the 60-day threshold. The many flags are consistent with the low precision; investigate due receipts and delivery feasibility before action.

## Verification and outputs

15 M5 tests cover strict cover/threshold boundaries, zero/missing history, weekday censoring, prior-only losses, future rows and modified future quantities, tied-score PR integrals, undefined metrics, exclusive-current labels, complete future windows, observed proxy false positives, policy constraints, export coverage, source separation and safe script embedding.

`output/m5/`: daily_inventory_risk.csv (150,600 rows), latest_risk.csv (150), monthly_availability.csv (396), risk_validation.csv, lost_sales_validation.csv, availability_validation.csv, protocol.json, risk.json and dashboard.html. The offline Dashboard supports retailer/category/status/month filters. Report month changes monthly availability and lost-sales tables only; latest stock remains as-of. Risk evaluation always shows the all-retailer/category held-out matched sample and ignores display filters. JavaScript/DOM filters were executed in a harness; no browser screenshot or Mac execution is claimed.

The current combined result and source fingerprint are in output/test_summary.json; PostgreSQL acceptance remains explicitly skipped until FMCG_TEST_DATABASE_URL points to a dedicated test database.

Completed release verification: **76 tests, 74 passed, 2 PostgreSQL skips**, 12 isolated source-fingerprinted batches.
