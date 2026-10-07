# Next steps after verified M0–M5

PostgreSQL acceptance is complete for the commit in RELEASE_EVIDENCE.md: 76 core tests passed with zero skips in GitHub Actions. The next phase is to make the offline portfolio demo reviewable and retain its evidence.

## 1. Retain and review the accepted demo

Download `synthetic-acceptance-37572311549` from the [verified run](https://github.com/Quetzel6/fmcg-analytics-platform/actions/runs/37572311549) before 2026-10-21. Retain the raw release, test, DQ and load reports with the generated dashboards. Follow DEMO_REVIEW.md to open and inspect M2–M5 in a real browser. Record the reviewed commit, browser, date and any issues; CI/DOM checks alone do not prove visual quality.

## 2. Review the portfolio narrative

Use DEMO_WALKTHROUGH.md for a 5–7 minute mentor/interview demo. Explain exact satang-to-baht conversion, KPI denominators, forecast selection and scenario limitations. Use synthetic figures only. Describe the verified database run and distinguish analytical order/inventory facts from an application API.

## 3. Add a separately versioned promotion scenario

Create a staggered promotion calendar if B2 needs an empirical benchmark. Keep the accepted default scenario and its evidence reproducible. Confirm control availability before comparing estimators. Truth remains validation-only.

## 4. Extend stock and order reasoning

Design a receipt-aware rule using only orders known at each prediction cutoff. Reserve a new unseen evaluation period; do not tune on the reported 2026 cohort. Specify inventory/order API requirements separately if building an operational service.

## 5. Build a Q4 SI planning scenario

Author a future synthetic promotion calendar and stock/replenishment bridge as detailed in M4_CLOSING_PLAN.md. Preserve M3's baseline, show incremental assumptions and avoid counting historical promotion effects twice. Do not treat SO uplift as a direct SI multiplier.

These extensions are not yet implemented. Publication, hosting and production operation are separate from passing the synthetic engineering gate.
