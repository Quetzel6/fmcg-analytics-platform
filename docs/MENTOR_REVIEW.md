# Mentor review: integrated synthetic FMCG platform

## Build and handoff

Run `python scripts/doctor.py`, then `python -u scripts/run_candidate.py --local`.
After success, run `python scripts/package_review.py` to create `output/mentor_review.zip`.
Extract the ZIP before opening `output/release_candidate.html`. Read `review_manifest.json`
for the exact candidate status and SHA-256/size inventory. The package snapshots outputs;
it does not establish that source code or output files have not changed since the build.
Local database verification remains pending even when a separate CI run passed.

The ZIP contains offline HTML, report JSON/CSV, Markdown documentation and selected
acceptance summaries. It excludes raw warehouse/truth data, source, virtual environments,
credentials and process logs. Keep the repository commit and CI URL beside the ZIP when
recording a review; the package does not infer a source commit from a loose checkout.

## Suggested 7-minute walkthrough

| Time | Page | What to explain |
| --- | --- | --- |
| 0–1 min | Release candidate | All data are synthetic. Explain SI versus SO, the as-of cutoff and local versus database certification. |
| 1–2 min | Default M2 | Select customer/category; show SKU growth, contribution and service. Explain filter denominators. |
| 2–3 min | Default M3 | Show historical backtests and annual target gap. Forecasts are estimates, not promised sales. |
| 3–4 min | Staggered promotion | Compare B1/B2 on matched promotions; explain rejected controls and uplift versus post-promotion dip. |
| 4–5 min | Receipt risk | Fewer false positives also come with worse recall and PR-AUC. The new rule is not a replacement detector. |
| 5–7 min | Q4 cockpit and ledger | Select scenario/customer/category; trace monthly SI to orders, receipt dates and residual target gap. |

The central authored Q4 plan adds THB 25,336.08 and leaves THB 459,317.05 overall gap
in the accepted scenario. Read generated outputs before quoting figures from a different
configuration. Scenarios are authored assumptions, not confidence intervals. Planned
orders are not submitted orders. SI growth alone does not establish promotion ROI.

## Review record

Record repository commit, candidate start/finish, browser/version, review date and pages
checked. Check a narrow window and Q4 scenario/customer/category filters. Record observed
issues with reproduction steps using `DEMO_REVIEW.md`. Automated acceptance does not
replace a browser visual review.
