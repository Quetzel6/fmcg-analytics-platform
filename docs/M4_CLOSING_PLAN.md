# Using M4 for a Q4 planning decision

## Correct monetary units

M3 raw money is **satang**, not baht. Divide `_satang` columns by 100 when presenting currency. Rounded default selected-method M3 outlook:

| Retailer | Annual shortfall (THB) |
| --- | ---: |
| ALL | 484,653.13 |
| C01 Meridian Market | 8,760.13 |
| C02 Summit Wholesale | 736,265.00 |
| C03 Willow Supermarket | −260,372.00 (surplus) |

ALL actual YTD is THB 27,758,999.50, Q4 baseline forecast THB 11,755,031.90, full-year outlook THB 39,514,031.40 and annual target THB 39,998,684.53. Values in previous narrative summaries treated satang as baht and overstated amounts 100-fold. The exact M3 CSV remains authoritative; no data or target is modified to manufacture attainment.

## Decision supported now

Prioritise C02 for scenario planning because its baseline gap is largest. Review C02 retailer/category **net** uplift together with stockout frequency and post-dip, rather than selecting solely by gross uplift. The M4 dashboard and category summary provide observed-unit evidence for this review. B1's pre-period baseline can confound seasonality/trend; all B2 rows lack clean controls, so the default dataset provides no controlled comparison. Avoid treating B1 as guaranteed causal uplift or promising closure of the monetary gap.

## Required contract before promotion-adjusted Sale-In scenarios

1. Author a separate Q4 planning calendar with retailer, SKU, dates, mechanic and discount. The default dataset has no Q4 2026 promotions; past promotion rows are not future plans.
2. Define incremental SO baseline relative to the selected SI baseline's implicit prior-year promotion activity. M3 already includes historical seasonality and promotion activity indirectly; adding the complete M4 uplift could double-count it.
3. Define initial stock, store availability, expected lead/delivery dates, case/MOQ rounding, delivery capacity and replenishment/closing-stock policy to bridge incremental consumer units into incremental retailer orders. Retail inventory replenishment is not identical to descriptive import lead-time attributes.
4. Convert delivered incremental SI units using applicable invoice prices on delivery dates. Retailer-funded SO discounts do not directly reduce SI invoice prices in this simulation. Include the post-promo dip and any Q1 spillover explicitly.
5. Compare baseline, conservative and optimistic scenarios; report uncertainty and feasibility. Keep the unadjusted M3 forecast visible, and label scenario assumptions separately from measured performance. Report additional delivered SI needed to close the gap; do not equate SO incremental value to SI revenue.

No plan, elasticity model, funding/margin or constrained replenishment bridge is currently supplied. Consequently M4 does not change the M3 forecast or claim improved forecast WAPE. To claim improvement, a promotion-aware SI model needs a historical backtest using only calendars and effects available at each origin; realised future effects cannot be training inputs. M5 remains the next milestone for stockout/risk evaluation.

## C02 category review (B1, all historical promotions)

| Category | Gross uplift % | Post dip % | Net uplift % | Promo stockout / promotions |
| --- | ---: | ---: | ---: | ---: |
| Canned Fish | 30.96 | −5.01 | 23.85 | 7 / 16 |
| Coffee | 37.92 | −2.28 | 34.91 | 18 / 24 |
| Oral Care | 22.18 | −4.99 | 15.93 | 10 / 16 |
| Snacks | 42.51 | −4.93 | 35.96 | 19 / 24 |

Coffee and Snacks are candidates to examine for a future scenario because their estimated net uplift is high, but their frequent observed stockouts make delivery/availability planning central to any scenario. These historical unit ratios are not forecasted incremental SI amounts. Cross-category differences also reflect different promo calendars and case mixes; they are not a controlled ranking.
