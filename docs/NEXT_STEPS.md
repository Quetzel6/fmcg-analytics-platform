# Current next steps

The integrated release candidate combines the environment fix, verified evidence documentation and supplemental analyses in one branch. Read `RELEASE_CANDIDATE.md` for the rebuild, CI contract and reviewed prior heads. Earlier PRs remain open, and main is unchanged until integration.

1. Require this integrated branch's own database-backed CI to pass; prior feature-branch successes do not certify the combination. Inspect candidate status, core tests and retained stage logs.
2. Review the generated `output/release_candidate.html` entry and all five links in a browser, including narrow windows and Q4 retailer/category/scenario filters. Record commit, browser, date and any actual visual defects using `DEMO_REVIEW.md`.
3. Review and merge the integrated PR when ready, then resolve overlapping earlier PRs. Keep the existing output evidence before artifact expiry.
4. Prepare the mentor/interview walkthrough with default results and separately labeled supplemental scenarios. Do not claim stronger risk detection, causal incrementality, forecast accuracy or profitability than the evidence supports.
5. Further modelling or operational API work needs a specified new scope and evaluation contract. Current analytical orders and authored incremental plans are not submitted orders or an inventory/order application service.
