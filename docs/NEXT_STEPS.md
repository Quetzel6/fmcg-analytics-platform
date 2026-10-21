# Current next steps

PR #7 merged the integrated candidate into main on 2026-10-08. Its pre-merge
head `3db96f8f4e24121cae797341080fb626c3c078e0` passed database-backed acceptance
in run 37604798122. This evidence belongs to that head, not later changes.

1. Rebuild main locally and record browser review using `DEMO_REVIEW.md`.
2. Build the offline review ZIP using `scripts/package_review.py`; follow
   `MENTOR_REVIEW.md` for the project walkthrough. Preserve the run
   status, repository commit and CI URL alongside the package.
3. Resolve overlapping older feature PRs after checking their scope; do not
   merge them blindly over the integrated history.
4. Operational APIs remain future work. Define inventory/order request contracts,
   idempotency, validation and persistence before implementing that service.
   Existing analytical orders and plans are not submitted orders.

Supplemental scenarios retain separate cohorts and assumptions. Do not claim
causal incrementality, improved recall, forecast accuracy or profitability beyond
the recorded evidence.
