# Verified release: 2026-10-07

## GitHub Actions evidence

- Repository: Quetzel6/fmcg-analytics-platform (private).
- Verified commit: `2c71373698e4b1ca610e3d7542611dcf3b933a81`.
- [Acceptance run #1](https://github.com/Quetzel6/fmcg-analytics-platform/actions/runs/37572311549): completed successfully.
- Job: `acceptance` / `112633445312`.
- Release: `status=passed`, `database_verified=true`.
- Core tests: **76 passed, 0 skipped**, 12 batches.
- Source SHA-256 reported by the runner: `03b5b4e8d90e206e97a3b1b7f4424cb46a7254b9213942b2b17bfdba157dc817`.
- Release started: 2026-10-07 04:37:25 UTC (11:37:25 Bangkok). Job completed: 04:40:44 UTC (11:40:44 Bangkok).
- Python 3.13; disposable PostgreSQL 16 service.
- Generation, strict DQ, database loading, M2–M5 reports/dashboards, demo, helper tests and core tests all exited successfully.

The job log was inspected in addition to the workflow's success badge. The core suite includes repeated loading, rollback after an injected failure, and M2 SQL/local parity. These results apply to this commit and default synthetic scenario; later code changes require a new run.

## Retained artifacts

Artifact `synthetic-acceptance-37572311549` (ID `11460987291`) was uploaded successfully. It expires on **2026-10-21** under the workflow's 14-day retention. Download it from the run page before expiry to retain the complete evidence.

Inspect `release_status.json`, `test_summary.json`, `all_test_results.txt`, `load_report.json`, `data_quality.json`, and `release_helper_tests.txt` inside the downloaded output artifact. This document is an evidence index, not a replacement for those raw files. The raw artifact was not downloaded during this documentation review.

The earlier Mac acceptance result supplied by the project owner was `passed`, with 2 integration tests passed, 0 skipped, `database_verified=true`, run ID `dc01a88a64914f589e4810e31a30f692`. That result is owner-reported; the GitHub run above was independently checked.

## Scope and limitations

Database acceptance closes the M1/M2 engineering verification gap. It does not establish real-data forecast accuracy, production operation, visual browser QA, a public hosted demo, or an inventory/order API. M4 still lacks clean B2 controls in the default calendar. M5's reported low precision remains unchanged. The temporary CI database does not populate the Mac's existing PostgreSQL container.
