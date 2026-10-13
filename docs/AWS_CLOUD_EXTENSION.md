# AWS Cloud Foundation extension

Verified through project-owner terminal evidence on 13 October 2026. The Cloud Foundation source is a separate project and has not yet been uploaded to GitHub. This repository's analytics dashboards remain offline outputs; they were not deployed by the cloud extension.

## Architecture and scope

A Python API and PostgreSQL 16 run in Docker Compose on a single Ubuntu 24.04 EC2 t3.small in Singapore. Encrypted 20 GiB gp3 EBS and IMDSv2 Required were observed in launch/instance screenshots. The API is bound to host localhost:8080; PostgreSQL has no host-published port. A Mac client accesses the API through an SSH tunnel on localhost:18080. Protected data endpoints use a shared Bearer token and a restricted PostgreSQL role. This is a personal lab using 100% synthetic data, not production or real customer consulting.

## Observed verification

| Check | Result |
|---|---|
| EC2 health | live 200, ready 200, missing route 404; both containers Healthy |
| Sales snapshot | 150600 rows; quantity 1931506; amount_satang 11929529809; 2024-01-01 to 2026-09-30 |
| API token checks | missing/wrong token 401; valid token 200 |
| API database role | sales SELECT allowed; UPDATE/DELETE/INSERT/truth/schema/temp/admin-role probes denied |
| Remote access | Mac SSH tunnel health checks passed; unauthenticated summary returned 401 |
| Backup restore | new restore database sales count, quantity, amount and date bounds matched the source |
| Off-host backup | dump copied to Mac; SHA-256 matched both hosts |
| Recovery | manual Compose startup succeeded after reported EC2 stop/start; data, auth and access checks passed |

Dump SHA-256: `bfafdb4feb78d61814b33727bf1020e1a3b4a0f613cb1283e8c623bef33f159e`.

Restore comparison covers sales aggregates, not every row/table. The dump used no-owner/no-acl and does not establish restored roles or permissions. Access checks after recovery used the active original database. No RTO/RPO or performance benchmark was measured.

## Limits and interview wording

The cloud extension does not deploy the analytics dashboard or establish production readiness. No public HTTPS endpoint, high availability, managed secrets, automated infrastructure, centralized alerts or executed cloud CI evidence is claimed. The single-host API/database architecture shares a failure domain. The loader retains an elevated lab owner identity. Compose requires a token, while standalone local operation without the token environment variable can bypass auth.

Describe the portfolio as a synthetic analytics platform with a separately verified AWS container/API/database extension. Do not attribute Cloud Foundation checks to this repository's acceptance workflow or describe portfolio work as years of Cloud Consultant employment.

## Pause and resume

Wait for active load/backup commands to finish, run `sudo docker compose stop` from the cloud-foundation directory, then Stop the existing EC2 instance in AWS Console. Do not Terminate: root storage is configured to be deleted on termination. Stop retains EBS storage cost. After Start, use the current public IPv4, update the SSH My IP rule if needed, and run `sudo docker compose up -d --wait` followed by health/data/auth/access checks. Do not recreate .env or reload the snapshot merely because the instance restarted.
