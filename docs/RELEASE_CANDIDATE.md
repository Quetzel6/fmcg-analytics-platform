# Integrated release candidate

The integrated candidate combines the reviewed documentation and Mac environment preflight with promotion, receipt-risk and Q4 planning/review work. PR #7 merged the integration into main on 2026-10-08. Prior PR and CI references describe historical scope; they do not certify later changes or establish the current state of other PRs.

## One-command local rebuild

Run from the source root in the working Python 3.13 environment:

```bash
source .venv-py313/bin/activate
python scripts/doctor.py
python -u scripts/run_candidate.py --local
open output/release_candidate.html
```

The environment check requires the pinned requirements. Existing working environments need no rename or deletion. If dependencies are missing, install `requirements.txt` using that active interpreter and retry. The source root contains `scripts/run_candidate.py`; a collection folder containing several extracted ZIPs is not the source root. See `MAC_SETUP.md`.

The command sequentially rebuilds the default release, staggered promotion benchmark, reserved receipt-risk benchmark and authored Q4 ledger/cockpit. The default release runs all Python helper tests, including environment, orchestration and Q4 presentation checks, plus the core suite. A local success is `passed_local_database_pending` and never certifies a database. Local mode removes inherited database URLs before launching subprocesses.

The navigation page is retained only after every stage succeeds, accepted fresh default release evidence exists and every linked page was regenerated during the attempt. Build inputs are hashed before and after execution; a change during the run fails the candidate. Successful status includes input and artifact SHA-256/size inventories. The review packager compares both inventories and requires a rebuild after changes. An old candidate navigation page is removed at startup and on failure. On failure, read `output/candidate_status.json` and `output/candidate_<stage>.txt`; earlier output files may still exist but do not constitute a successful candidate.

## Database-backed CI

CI runs `python scripts/run_candidate.py` with its disposable PostgreSQL 16 service. The default release must return `passed`, `database_verified=true` and complete core-test certification. The supplemental commands must also succeed. The generated Q4 filter script is tested separately with Node in CI; Node is not needed to run the local Python build or view HTML in a browser.

Candidate `database_verified` describes the default warehouse acceptance only. Supplemental promotion, risk and planning results retain their separate cohorts, assumptions and status evidence. A failed supplemental stage leaves the candidate failed even if its default warehouse verified successfully. Artifacts are retained for 14 days under the existing CI policy.

## Prior verified heads

| Change | Verified head | Successful CI runs |
| --- | --- | --- |
| Original default warehouse | `2c71373698e4b1ca610e3d7542611dcf3b933a81` | 37572311549 |
| Authored Q4 ledger (#5) | `68dd1edccddaabb63662d4350debad361b7c4701` | 37600898284, 37600839310 |
| Commercial review (#6) | `721306ffe8d3131ccec5c533b28a7d1392c129c6` | 37603142857, 37602924842 |

These successes belong to those heads. Every subsequent change requires its own acceptance evidence; prior badges do not certify it. `RELEASE_EVIDENCE.md` retains the original raw-evidence index.

## Review each rebuilt candidate

Open `release_candidate.html` and review each page with its respective documentation. Browser visual review remains distinct from automated tests. The default M3 forecast and targets remain unchanged. The default M4 still lacks clean B2 controls; the staggered calendar supplies a separate comparison. The reserved receipt-risk rule has fewer false positives but worse recall and PR-AUC. The central authored Q4 plan adds THB 25,336.08 and leaves an overall THB 459,317.05 shortfall; it does not prove forecasting accuracy or promotion profitability.

No production deployment, public hosting, actual order submission or real business data is added. Check the scope and current state of historical overlapping PRs before taking any merge action.
