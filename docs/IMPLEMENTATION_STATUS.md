# Implementation status

Current engineering acceptance: [GitHub Actions run #1](https://github.com/Quetzel6/fmcg-analytics-platform/actions/runs/37572311549), **76 core passes / 0 skips**, with `database_verified=true`. Scope and commit: [RELEASE_EVIDENCE.md](RELEASE_EVIDENCE.md).

| Work | Status |
| --- | --- |
| M0 scenario config / spec review | Implemented |
| M1 seeded daily generator / CSV / manifest | Implemented; reproducibility checked by CI |
| DQ-01–DQ-17 | Strict gate and mutation checks passed in CI |
| PostgreSQL DDL / COPY / post-load reconciliation | Passed on disposable PostgreSQL 16 |
| Repeat load / injected rollback | Real integration test passed |
| Truth boundary | Separate files/schema; source boundary guards tested |
| M2 commercial / service KPIs and SQL views | Local exports and four-view SQL parity passed |
| M3 backtests / Q4 baseline / closing dashboard | Implemented; synthetic benchmark and leakage checks |
| M4 promotion estimators / dashboard | Implemented; B1 240 promotions; B2 unavailable without clean controls |
| M5 inventory / risk dashboard | Implemented; held-out low precision remains explicitly reported |
| Combined offline demo | Generated in CI; browser visual review still outstanding |
| GitHub acceptance workflow | Successfully executed; logs/output artifact retained for 14 days |
| Inventory/order application API | Not implemented; current order/inventory facts are simulated analytical inputs |
| Public hosted website / production deployment | Not implemented |

Earlier results of 24/34/47/59/74 local passes belonged to successive milestones and excluded available database tests. The latest verified core result is 76/76; future runs must be assessed from their own logs and source fingerprints.

Local `--local` rebuilds still report `passed_local_database_pending` because they deliberately do not connect to PostgreSQL. That describes the individual local run, not a reversal of the verified CI result.

The existing Mac database is separate from the disposable acceptance databases. Successful CI does not imply it contains the generated warehouse. See NEXT_STEPS.md for the remaining work.
