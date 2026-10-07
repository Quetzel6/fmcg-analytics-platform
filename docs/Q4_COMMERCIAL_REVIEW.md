# Q4 commercial review

This offline presentation extends the authored Q4 ledger in `Q4_PLAN_V1.md`. It adds a review workflow without changing the forecast, annual targets, order-sizing policy, input data or monetary results.

## Run

Activate the existing project Python environment, then run from the repository root:

```bash
python -u scripts/run_release.py --local
export PYTHONPATH="$PWD/src"
python -m fmcg.q4_plan
open output/scenarios/q4-plan-v1/cockpit.html
```

The default release rebuild is required when switching from a branch whose generator differs. The planning command still checks strict DQ before exporting. No new Python dependencies are required. The dashboard works from a local file without a web server or external assets.

## Review workflow

1. Select conservative, central or optimistic; the page initially selects central. These are assumptions, not confidence intervals.
2. Select a retailer and category. Monthly rows and order reviews follow all three filters. Selecting ALL retailers shows the category/month rows for each retailer, not a fabricated consolidated category target.
3. Read the annual bridge: annual target, unchanged baseline outlook, extra Q4 SI, scenario outlook and remaining gap. This section follows scenario and retailer only. Category selections do not change a retailer's annual target; targets have not been allocated to categories or months.
4. Read October–December category/month SI as baseline forecast plus incremental receipts. These are projected amounts, not assigned sales targets. Categories and retailers without authored orders retain baseline values and remain visible.
5. Review order dates, expected receipt dates, requested versus planned cases, SI units, Q4 versus Q1 SI, unserved incremental SO and residual delta stock. These quantities do not imply actual orders or confirmed receipts.

`actions.csv` exports the same order-review rows. If an incremental order has zero cases, its state is `No incremental order` and its operational dates are blank; the original hypothetical dates remain in the underlying ledger. No order-submission integration is added.

Review flags describe observed ledger conditions: capacity limited, unserved incremental SO, Q1 receipt, post period crossing into Q1 and residual incremental stock. They are not fitted risk scores or thresholds. An unserved quantity is not backfilled. Extra SI remaining in stock does not establish additional consumer sales or promotion profitability.

## Evidence and validation

- 108 monthly rows, 12 annual rows and 12 order-review rows across three scenarios.
- The exporter checks unique monthly grouping, baseline-plus-increment identities, delivery/monthly/annual incremental reconciliation and annual target identities before writing the cockpit.
- Money displays exact rational amounts via decimal arithmetic. CSV/JSON evidence remains authoritative for fractional amounts and rounded display differences.
- Six presentation tests cover filter grouping, zero-order dates, capacity/Q1/stock flags, failed reconciliation, HTML escaping and large exact money values.
- The generated page's actual JavaScript is exercised in a Node VM without browser packages: default central scenario, retailer/category isolation, empty order scopes, annual scope and scenario switching.
- The ten existing Q4 ledger tests and source-boundary guard pass locally. Acceptance CI runs the default PostgreSQL release, supplemental scenarios, Q4 Python tests and filter-script check.

The central plan still adds THB 25,336.08 and leaves an overall gap of THB 459,317.05. More actions or targets are not invented to close that gap. See `Q4_PLAN_V1.md` for incrementality, prices, stock accounting, scenario transfer and other limitations. This change is stacked on PR #5.
