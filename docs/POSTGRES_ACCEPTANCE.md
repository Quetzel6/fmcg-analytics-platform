# Dedicated PostgreSQL acceptance

The bundled automation creates **its own temporary PostgreSQL 16 Docker container**, binds a randomly allocated localhost port, and supplies a fresh credential in a private temporary env file. It does not use DATABASE_URL, the existing Compose volume or an existing company database. Generated credentials are not printed or retained in test logs.

From the extracted project root, with the Python virtual environment activated, dependencies installed and Docker Desktop running:

```bash
python3 scripts/accept_postgres.py
```

Docker may download the postgres:16 image on the first run. The Python environment needs `requirements.txt`, including psycopg. The owner reported a successful dedicated Mac run on 2026-10-07. The complete GitHub Actions rebuild independently passed real PostgreSQL 16 integration with zero skips. See RELEASE_EVIDENCE.md; the temporary-container runner and CI service use different database lifecycles.

The automation runs the two real integration tests without allowing skipped/incomplete output to count as success: repeated load and rollback after injected failure, then SQL/local M2 view parity. Finally it loads the default dataset and requires a committed load with post-load reconciliation passed. It removes only the container bearing this run's ownership label, including its temporary anonymous data volume. Timeout, interruption and test failures also trigger ownership-checked cleanup; cleanup status is recorded.

Evidence is retained under `output/postgres_acceptance/<run_id>/`:

- `integration_tests.txt`: completed actual integration log, with generated credentials redacted.
- `load_report.json`: actual final snapshot load evidence, only reached after successful tests.
- `summary.json`: passed / failed / blocked / interrupted and cleanup status.
- `output/postgres_acceptance/latest.json`: latest attempt pointer/status.

Exit code 0 requires successful actual integration; blocked/failed/interrupted attempts exit 2. A current `blocked` report means the database remains unverified. Offline automation tests use mocks to verify lifecycle and failure handling; they do **not** certify PostgreSQL or SQL parity. The original 76-case local test summary is unchanged; helper test evidence is separate.

To rerun the complete existing suite against another dedicated database, use the documented FMCG_TEST_DATABASE_URL workflow in README; it replaces project schemas. The default automation avoids this manual database selection by owning its disposable database.
