# Implementation status

| Work | Status |
| --- | --- |
| M0 config/repository/spec review | Implemented |
| M1 seeded unified generator / CSV / manifest | Implemented and locally exercised |
| M1 DQ-01..15 and pre-load manifest checks for DQ-16 | Implemented; mutation tests cover each rule |
| M1 DQ-17 sanity | Implemented; warning in loader, blocking in tests |
| PostgreSQL DDL/COPY loader / DQ-16 after insert | Implemented, database integration not executed in this environment |
| Repeat DB load / rollback after inserted rows | Integration test supplied; skips unless FMCG_TEST_DATABASE_URL is set |
| Truth boundary | Separate files/schema; PUBLIC privileges revoked; guard for future analytics/forecast/uplift/risk source directories |
| M2 C01–C10/S01–S07 and offline Dashboard | Local calculation and exports implemented; SQL parity integration test pending |
| M3 F01–F04/C11–C12, two-origin backtest and closing Dashboard | Locally implemented; benchmark, leakage and reconciliation tests included |
| M4 P01–P07 and offline promotion dashboard | Locally implemented; B1 all 240, B2 no clean controls in default scenario |
| M5 S08–S11 / R01–R04 and offline Dashboard | Locally implemented; fixed-rule held-out validation, low precision explicitly reported |

M1 is a locally validated implementation candidate, not a fully accepted PostgreSQL milestone. Do not describe PostgreSQL repeatability/rollback as verified until the optional database test runs successfully. The local gate's DQ-16 verifies CSV checksums/counts/amounts; load_report.json is the evidence for the database stage when run.

Do not carry over earlier-release test counts, dashboard screenshots, Jan–Aug dates or independent supply metrics into this daily-contract project. No application has been run on the user's Mac, no remote Git repository created and no data pushed.

Release verification: 24 local tests passed; 1 PostgreSQL integration test skipped. Tests exercised the full default panel, all DQ rule mutations, seed/config/code reproducibility, ground-truth counterfactual coupling, and date/KPI edge cases. See output/history/m0m1_tests.txt.

M2 adds 10 local tests and one optional PostgreSQL view parity test. The combined release evidence is output/all_test_results.txt. Database acceptance remains pending for M1/M2.

Historical M0–M2 acceptance: 34 local tests passed in six isolated batches; 2 PostgreSQL integration tests skipped. Complete case logs and source fingerprints are retained under output/checks/. The combined summary is output/test_summary.json.

M3 source formulas, selection rules and acceptance evidence are in M3_ACCEPTANCE.md. M3_BENCHMARK.md reports default-scenario historical WAPE/Bias, not real-data accuracy.

Historical M0–M3 release: 49 test cases, 47 local passes, 2 PostgreSQL integration skips, across 8 isolated source-fingerprinted batches. See output/test_summary.json and output/all_test_results.txt. M3 has 13 passing cases.

Historical M0–M4 release adds 12 local M4 tests. See output/test_summary.json for the complete current count and M4_ACCEPTANCE.md / M4_CLOSING_PLAN.md for coverage and the SI planning boundary. M5 local implementation and fixed-rule limitations are in M5_ACCEPTANCE.md.

Historical verified M0–M4 release: **61 tests, 59 local passes, 2 PostgreSQL integration skips**, 10 isolated source-fingerprinted batches. The database acceptance limitation is unchanged.

M0–M5 local code now includes 15 M5 tests and inventory/risk exports. See current output/test_summary.json for release verification; database integration remains pending. Next steps are in NEXT_STEPS.md.

Verified current M0–M5 release: **76 test cases, 74 local passes, 2 PostgreSQL integration skips**, across 12 isolated source-fingerprinted batches.

Post-M5 acceptance/demo tooling: combined offline entry page, mentor/interview walkthrough and disposable PostgreSQL acceptance runner supplied. Eight independent offline helper tests passed; actual database run is blocked (no Docker), not accepted. Existing M0–M5 source fingerprint and 76-case evidence are unchanged.

CI/release stage: full local regeneration and M2–M5 report rebuild completed successfully; core 74 passes / 2 database skips plus 13 helper passes. Release status is passed_local_database_pending. Workflow YAML was parsed locally; GitHub CI and actual PostgreSQL execution remain unverified. See CI_RELEASE.md and output/release_status.json.
