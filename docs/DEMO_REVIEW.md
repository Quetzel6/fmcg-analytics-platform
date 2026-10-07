# Offline demo review

## Open the accepted output

Download the output artifact from the acceptance run linked in RELEASE_EVIDENCE.md and extract it without changing the relative directory layout. Open `index.html` at its root. The artifact contains outputs; it is not a source checkout.

Alternatively, from an existing source checkout with Python 3.11+ and requirements installed:

```bash
source .venv/bin/activate
python -u scripts/run_release.py --local
open output/index.html
```

On macOS, `open` launches the default browser. Wait for the rebuild to finish before opening the pages. A local-mode success is not an additional database test.

## Review checklist

| Page | Check | Expected boundary |
| --- | --- | --- |
| Entry | All four dashboard links open | Relative links work after extraction |
| M2 | Retailer, SI/SO, category filters; labels and chart/table layout | Category does not redefine contribution/rank denominators; service remains retailer-level |
| M3 | Backtest origins, selected method, annual outlook and gap | THB 484,653.13 ALL shortfall in the accepted default scenario; raw money is satang |
| M4 | Promotion results, stockout coverage and unavailable B2 reasons | B1 240 promotions; no fabricated B2 controls or direct SO-to-SI adjustment |
| M5 | Retailer/category/status/month filters and latest snapshot | Latest as-of 2026-09-30; precision 6.24% and recall 92.30% labelled as matched held-out results |
| All | Narrow window, readable text, no clipped charts/tables | No real company data or production accuracy claims |
| All | Browser console and links | Record actual errors with page and filter selection |

Record: commit/run, browser/version, review date, each check result, and screenshots of the four default views. Browser review has **not** yet been completed by this documentation change.

## Suggested demo order

Follow DEMO_WALKTHROUGH.md: data contract and DQ → M2 actuals → M3 target gap → M4 promotion limitations → M5 risk limitations → verified database/CI evidence.

Keep the raw acceptance artifact before its expiry. Model improvements, operational APIs and hosting remain separate next steps.
