# M4: observed promotion estimators

Implemented P01–P07 locally for the default synthetic as-of 2026-09-30. No promotion effects are applied to the M3 Sale-In forecast. PostgreSQL integration remains pending.

## Estimator contract

The treated series is daily Sell-Out units summed across a retailer's stores for one SKU. Windows are 28 days before start, inclusive promotion start/end, and 14 days after end. Inputs are only warehouse sales, inventory, store/product dimensions and the promotion calendar. DQ validation gates exports. All arithmetic is exact Fraction; CSV/JSON decimal representations have 50-digit precision, and detail-level rational evidence is exported separately.

B1 baseline on day d is the mean of the four matching weekdays in the pre-window. B2 is an **additive difference-in-differences estimator with pre-period unit scaling**: baseline(d) = treated weekday mean + scale × (control observed units(d) − control pre weekday mean), where scale = treated pre units / pooled control pre units. Controls are other retailers selling the same SKU, pooled in units. Each control must have complete observations and no promotion or its 14-day post-period intersecting any of the treated pre/promo/post window. This estimates an additive common time change under parallel trends after unit scaling; it does not establish causal identification from simulation output alone.

Negative daily B2 baselines, zero baselines, incomplete windows, contaminated treated windows and missing clean controls are explicit unavailable statuses, with no fabricated zero effect. Full calendar coverage is retained. Future observed quantities and inventory are filtered at as-of.

P02 incremental = promo actual − promo baseline. P03 uplift = incremental / promo baseline × 100. P04 post dip = post incremental / post baseline × 100. P05 net = (promo incremental + post incremental) / promo baseline × 100. Group effects use ratios of summed units, not simple averages of promotion percentages. Coverage columns accompany every group; null effects remain null when no valid estimates exist.

P07 promo censoring means at least one store has observed closing_qty = 0 on a promo day. This is an observed stockout proxy, not inferred lost demand. A separate post_censored flag supports post-dip validation. Summary cohort `uncensored` excludes promo-censored rows; post-dip MAE's uncensored cohort instead excludes post-censored rows. The two validation sample counts are explicitly different.

P06 runs in `promotion_validation.py`, outside estimator/forecast directories. Only this validation stage reads planted effects; estimators never use them. Bias/MAE are percentage points versus planted demand multipliers and include realised sampling noise. Unavailable estimates are omitted from errors with reported counts, never imputed.

## Default benchmark

- 240 promotions × 2 methods = 480 rows.
- B1: 240 available; 152 promo-censored, 88 without promo stockouts.
- B2: all 240 unavailable (`no_clean_control`). The authored retailer slots overlap the expanded 28-day pre and 14-day post windows. B2 cannot be empirically ranked against B1 on this dataset.
- B1 uplift all: bias +0.69 pp, MAE 9.60 pp (N=240).
- B1 uplift without promo stockouts: bias −0.05 pp, MAE 6.88 pp (N=88).
- B1 post dip all: bias +3.81 pp, MAE 6.73 pp (N=240).
- B1 post dip without post stockouts: bias +4.13 pp, MAE 6.61 pp (N=193).

These cohorts differ in composition; lower MAE is not proof that removing stockouts improves the same promotion's estimate. B2 formula tests include an eligible control fixture with known common-trend and treatment effects, zero/absent controls and negative-baseline handling. A later scenario may stagger promotions to create untreated controls; the default scenario and M3 benchmark are preserved.

## Review and verification

12 M4 tests cover known uplift/dip/net, weekday adjustment, common-trend DiD, missing/zero/negative cases, all promotion coverage, weighted group denominators, validation separation, future observation cutoff, CSV/JSON exports and script escaping. Offline dashboard JS tables and all three filters were executed in a DOM harness; no rendered browser screenshot or Mac execution is claimed. Full release test counts are in `output/test_summary.json`.

Deliverables: `output/m4/promotion_estimates.csv`, `retailer_category_summary.csv`, `validation_errors.csv`, `validation_summary.csv`, `promotion.json`, `rational_exact.json`, `dashboard.html`. The detail dashboard retains unavailable rows and reasons; validation is separately labelled and always uses all-retailer samples even when the retailer display filter changes.

Complete release verification: **61 tests / 59 passed / 2 PostgreSQL skips** across 10 isolated batches.
