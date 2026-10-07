# Next steps after local M0–M5

M0–M5 local methods are implemented with synthetic validation. Remaining acceptance work should be explicit rather than described as completed.

1. Run PostgreSQL integration on a dedicated disposable database: loader DDL/COPY/reconciliation, repeat load, injected rollback and M2 SQL parity. Use DATABASE_URL for loading and FMCG_TEST_DATABASE_URL for integration tests; retain actual load_report.json and completed test logs. Docker/PostgreSQL server is unavailable in the current execution environment.
2. Review the M4 missing-control calendar limitation and M5 high false positive rate before making portfolio accuracy claims. Author a separately versioned scenario with staggered promotions if a B2 empirical benchmark is desired. A new risk rule with known open-order information needs a reserved, unseen evaluation period; do not tune on the reported 2026 cohort.
3. For a promotion-adjusted Q4 SI plan, supply a future calendar and a stock/replenishment bridge as detailed in M4_CLOSING_PLAN.md. M3 baseline forecasts are unchanged. No raw planted effects may enter training or planning estimates.
4. For portfolio publication, provide a concise architecture/demo walkthrough and selected synthetic findings with denominator, coverage and limitation labels. The original spec copies remain in docs/source_specs/. No GitHub repository or remote publication has been created here.

These are review/acceptance and portfolio tasks; local completion is not a production-deployment claim.

Demo entry page and walkthrough are now supplied. Dedicated DB acceptance automation is supplied in scripts/accept_postgres.py; its local attempt is blocked by missing Docker, so step 1 still requires an actual execution environment with Docker and dependencies.

A reproducible release runner and GitHub Actions PostgreSQL acceptance workflow are now prepared. The next external acceptance step remains an actual dedicated-DB/CI execution; neither a prepared workflow nor local helper tests certify SQL parity.
