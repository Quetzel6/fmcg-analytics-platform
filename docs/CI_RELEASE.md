# Reproducible rebuild and CI acceptance

The project now supplies a single sequential rebuild command plus a GitHub Actions workflow. The workflow file has been parsed locally but **has not run on GitHub**. No remote repository has been created or pushed.

## Local rebuild

Activate the virtual environment and install requirements, then run:

```bash
python3 scripts/run_release.py --local
```

This regenerates disposable synthetic data, runs strict DQ, rebuilds all M2–M5 reports and dashboards, builds the demo entry page, runs helper tests and reruns all core tests. It stops at the first failed stage. Local mode removes inherited DATABASE_URL and FMCG_TEST_DATABASE_URL from child environments, so it cannot accidentally connect to a database. Its successful status is explicitly `passed_local_database_pending`, never a database certification.

Default mode requires FMCG_TEST_DATABASE_URL for a dedicated disposable database; the loader replaces both project schemas. A complete database release requires all core tests with zero skips, a committed load and successful post-load reconciliation. Logs for each stage are written to output/release_<stage>.txt; final status is output/release_status.json. Run status is authoritative for the complete pipeline; individual report files may remain from earlier or incomplete runs after a failure. Do not interpret their presence as a completed release.

## GitHub workflow

When the project contents become the repository root, `.github/workflows/acceptance.yml` runs on push, pull requests or manual dispatch. It uses a temporary PostgreSQL 16 service, Python 3.13 and pinned Python dependencies, then invokes the database-required rebuild command. It retains output logs/reports for 14 days even when a step fails. The explicit CI password is only a disposable test fixture for that job; no real account credentials are required.

The initial checkout is expected to have no data/ or output/ because these generated folders are ignored. The workflow regenerates all report artifacts **before** running tests that inspect them. The service database is dedicated to the job; no company database or external account is used. Workflow action tags and real GitHub service behaviour remain to be exercised by an actual run.

The core suite includes the real PostgreSQL repeated-load/rollback test and M2 SQL/local parity test. Skipped tests fail database release certification instead of producing a misleading pass. Local orchestration tests additionally cover stage ordering, skip rejection, missing-database blocking, early failure and inherited-credential removal. They are not substitutes for PostgreSQL execution.

## Reading evidence

- output/test_summary.json: current 76-case core result and source fingerprint.
- output/release_helper_tests.txt: the helper/orchestration test log for this rebuild.
- output/release_status.json: whether this complete rebuild succeeded locally or passed actual database acceptance.
- output/load_report.json: actual database load evidence if default mode reached the loader.
- output/index.html: rebuilt offline Demo entry page.

For a Docker-only temporary acceptance run, keep using scripts/accept_postgres.py; see POSTGRES_ACCEPTANCE.md. That runner owns and cleans up its own disposable container. The CI runner uses the service lifecycle managed by the CI job instead.

Actual local rebuild completed with 74 core passes / 2 database skips and 13 helper passes. Rebuilt M2–M5 JavaScript and customer filters were executed locally with scripts/check_dashboards.cjs; this is DOM verification, not visual browser QA. The harness is retained in the project rather than temporary storage.
