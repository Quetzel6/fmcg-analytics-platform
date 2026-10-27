# Review map: synthetic reliability case study

All data and business scenarios are synthetic. No company data or actual business
impact is claimed. Read RELIABILITY_CASE_STUDY.md first, then the generated run.json
and five stage JSON files. The expected P01 Jan–Sep 2026 SI is THB 7,167,417.60 before
and THB 7,205,061.60 after: 37,644 delivered units × THB 1 revised invoice price.
Grain is order_id + line_id; recognition uses delivered_date, not order_date.
This is a full snapshot correction. Open lines contribute zero; volumes and targets
are unchanged. Rejected data and failed transactions must leave published totals intact.

## Complete change map

This branch includes the preceding audit changes from the same chat, which the
case study reuses. There are no changes to other repositories, model algorithms,
cloud infrastructure, dependency versions or the production loader transaction.

| File | Role |
| --- | --- |
| scripts/case_study.py (new) | Synthetic fixtures, existing loader/report calls, failure injection and run evidence |
| scripts/test_case_study.py (new) | Five real PostgreSQL regressions, raw CSV grain/amount checks and cleanup |
| docs/RELIABILITY_CASE_STUDY.md (new) | Brief, definitions, executable walkthrough, limitations and interview answers |
| docs/FINAL_REVIEW.md (new) | Reviewer navigation and complete file map |
| README.md | Case-study entry point and provenance packaging instructions |
| .github/workflows/acceptance.yml | Existing dashboard checks and dedicated case-study integration job step |
| src/fmcg/validate.py | Earlier audit: malformed manifest and invalid positive dimensions fail DQ cleanly |
| tests/test_m1.py | Earlier audit: three DQ regression tests |
| scripts/evidence.py (new) | Earlier audit: build input and artifact checksum inventories |
| scripts/run_candidate.py | Earlier audit: reject inputs changed during a build |
| scripts/package_review.py | Earlier audit: reject stale/modified candidate inputs and artifacts |
| scripts/test_candidate.py | Earlier audit: changing-input failure regression |
| scripts/test_package_review.py | Earlier audit: altered input/artifact and missing-provenance regressions |
| docs/REPOSITORY_AUDIT.md (new) | Earlier audit scope and interpretation boundaries |
| docs/IMPLEMENTATION_STATUS.md | Identify historical evidence as historical |
| docs/MENTOR_REVIEW.md | Explain new checksum checks and their limits |
| docs/RELEASE_CANDIDATE.md | Correct obsolete pre-merge wording and describe provenance |

Generated data, reports, logs, ZIPs, environments and local credentials remain
ignored. Commit only the files above. Review the staged diff and sizes before push.

## Evidence boundaries

- DQ rejection: invalid amount/checksum fails before load; dq_rejection.json records
  unchanged count, SI total and KPI.
- Rollback: actual corrected inserts and reconciliation run inside a transaction;
  an injected application exception before commit restores previously published values.
- Recovery: rerun the valid corrected snapshot after removing that injected fault.
- Repeat: same snapshot gives the same row count, total and KPI.

This does not test power failure, network outage, automatic retries, crash-safe
monitoring, incremental ingestion or production scale. It provides no causal
promotion, profit or real-market accuracy claim. Human browser visual review and
remote GitHub CI are separate from local command execution.

Actual new test times/counts and run IDs belong in the PR's validation section;
do not reuse the 26 October 79-core result as current evidence.
