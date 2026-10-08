# M4 supplemental staggered calendar: v1

This versioned synthetic scenario enables an empirical B1/B2 comparison without changing `config/scenario.toml` or the default M3 outlook.

## Run

From the source root, with the working Python environment active:

```bash
export PYTHONPATH="$PWD/src"
python -m fmcg.promotion_scenario
open output/scenarios/staggered-v1/benchmark.html
```

The command generates a separate dataset at `data/scenarios/staggered-v1/`, applies strict DQ, completes observed estimates before planted-effect validation, and writes M4 exports plus a dashboard and a matched benchmark page at `output/scenarios/staggered-v1/`. It connects to no database and does not overwrite the default dataset, M4 report or M3 forecast. Do not load this scenario into the default database without an explicit separate scenario/database plan.

The CI workflow runs this supplemental command after the default database-required release and uploads its outputs with the acceptance artifact. The main `release_status.json` certifies the default release; `scenarios/staggered-v1/benchmark_status.json` records the supplemental run. Workflow success requires both commands to succeed.

## Calendar contract

| Retailer | Full-year months | Final-year months (2026) | Start day |
| --- | --- | --- | ---: |
| C01 | February, June, October | February, June | 5 |
| C02 | March, July, November | March, July | 15 |
| C03 | April, August, December | April, August | 25 |

Per-customer override keys are `promotion.customer_months_full_year` and `promotion.customer_months_final_year`. Absent overrides fall back to the existing global calendar. Unknown customers, duplicate/unsorted/noninteger/out-of-range months and start days outside 1–28 are rejected before simulation. Promos whose pre/post windows exceed observed history are still excluded by the existing generator contract.

Length, discount, seed, demand, replenishment, disruptions and estimator formulas are unchanged. Altering the calendar changes the simulation's realized demand and inventory, so its totals must not be compared as an isolated causal effect of scheduling.

## Observed supplemental result

Executed locally with NumPy 2.3.5. Strict DQ-01–DQ-17 reported zero findings. There are 240 promotions, 150,600 daily sales rows and 150,600 inventory rows.

- B1 available: 240/240.
- B2 available: 239/240.
- Unavailable B2: 1 negative daily baseline, retained with its reason.
- Matched comparison: 239 promotions available to both methods.

| Method | Matched N | Uplift Bias (pp) | Uplift MAE (pp) | Post-dip MAE (pp) |
| --- | ---: | ---: | ---: | ---: |
| B1 | 239 | -1.17 | 8.59 | 8.82 |
| B2 | 239 | -0.76 | 11.07 | 7.68 |

On this matched cohort, B1 has lower uplift MAE; B2 has lower post-dip MAE. B2 is not selected as universally superior. Full precision, all-available cohorts and separately defined uncensored uplift/post cohorts are retained in `benchmark_status.json`.

The promotion dashboard displays all-available method validation, while `benchmark.html` displays matched-cohort validation. Use the matched page to compare methods fairly. Uplift uncensored excludes promo stockouts; post-dip uncensored excludes post-window stockouts, so their counts can differ.

Eligibility excludes controls with overlapping promotions or post-dips across the complete treated pre/promo/post window. It does not prove parallel trends: retailer weekday profiles, monthly seasonality, stock censoring and noise remain limitations. This is validation on synthetic planted effects, not real-world causal identification, promotion ROI or an SI planning adjustment.

## Verification and reproducibility

The supplemental dataset was regenerated and its complete manifest reproduced. The default scenario was also regenerated after the generator change: all default CSV file checksums, counts and raw amount totals remained identical to the prior default manifest. The generator hash changes because support for optional calendar overrides was added; manifests must therefore be regenerated with the current code before DQ/loading.

Seven targeted tests cover fallback/override calendars, invalid configuration, clean control eligibility, contamination from a control's post-dip, matched counts and the benchmark page. The full local core regression completed with 74 passes and 2 PostgreSQL skips (76 total), across 12 batches, source fingerprint `f41cf838bc4f5f45bd3463808a81dacdb2973d868b49701b275042e5ac6ff18c`. Default M2–M5 reports were rebuilt before the suite. Fresh PostgreSQL integration must be read from this PR's CI run; the old accepted commit alone does not certify this change.

Next modelling work remains receipt-aware risk on a new reserved evaluation period and an explicit Q4 stock/replenishment bridge. This scenario does not tune the reported 2026 risk cohort or alter the accepted M3 baseline.
