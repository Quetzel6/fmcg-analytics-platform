# Spec review and decisions — v0.2, 2026-10-05

The two supplied v0.1 drafts are the authoritative starting point for this release. Original files are preserved verbatim under `docs/source_specs/`. Reviewed copies below record corrections and explicit implementation choices. They supersede the earlier monthly, independent SI/SO/supply demo; that dashboard does not consume this new dataset.

## Understanding and opinion

This is a methods-validation portfolio, not a recreation of company data. Its value is a coherent simulation, auditable money/quantity definitions, exact reconciliations, reproducibility and later held-out evaluation. The 2024 history is necessary for the Q4 2025 seasonal baseline backtest. SI recognition belongs to delivered order lines, not generated independent monthly sales. The explicit ledger is the stock source; a difference between SI and SO is not a stock balance.

The drafts provide sufficient structure to implement M0/M1. They do not prove completeness: tests must reveal contradictions, edge cases and implementation choices. Synthetic data should be generated from the authored fictional config without importing or calibrating to company records. Calling it automatically “100% NDA/PDPA safe” is not a defensible universal guarantee. This implementation uses no real company files, brand names or transaction prices. That is a concrete scope statement, not a legal certification.

## Corrections accepted here

1. **S05 inequality:** Order OTIF is not always ≤ Line OTIF because weighting differs. Counterexample: nine single-line orders pass; a tenth order has ten failed lines. Order OTIF = 9/10 = 90%, Line OTIF = 9/19 ≈ 47.37%. Keep both definitions and remove the universal inequality; a unit test preserves this correction.
2. **DQ-04 horizon:** Observed dates must lie within 2024-01-01..2026-09-30. `promised_date` may extend past as-of, and `fact_target_monthly` covers the full 2025/2026 calendar years. Neither field is future actuals. The observed dim_date has exactly 1,004 rows; target months and future promises therefore do not use a dim_date FK.
3. **Short shipments:** A positive short delivery closes the line; its undelivered remainder is cancelled. Only NULL-delivery lines belong in backlog. The old demo's all-lines remainder backlog must not be reused.
4. **Money:** Shelf/invoice/discount prices are rounded to integer satang with Decimal `ROUND_HALF_UP`; amount is then quantity × the rounded unit price. The same rule is used by generator and validator. PostgreSQL money aggregates cast to NUMERIC. No floating-point money aggregation is used.
5. **Reproducibility:** Same seed alone is insufficient. Same config, generator code and pinned NumPy are required. The manifest stores all three hashes/version context; there is no timestamp that would break repeatability.
6. **Truth interpretation:** Planted `true_uplift_pct` and `true_post_dip_pct` describe demand multipliers, before stock censoring, not the realised noisy ratio of observed sales. Later M4 must describe that estimation target and report censored windows separately. Boundary promotions lacking pre/post history are excluded by generation. Baseline and latent draws are coupled using Poisson superposition during uplift and binomial thinning during post dip. With no promo effect, latent equals baseline; promoted latent is at least baseline, dipped latent is at most baseline.
7. **Bootstrap:** For the first 14 days the reorder estimate has a configured base-rate floor because there is no historical sales window yet. Thereafter it uses only observed sold quantities over up to 14 days. `numpy.std` uses the population standard deviation (`ddof=0`). No truth-demand values feed the planner.
8. **Delivery model:** One store/day order can have multiple SKU lines with separate delivery dates. Early delivery remains on/after order date. Disrupted deliveries are at least one piece when their delivery is observed; any quantity rounded below one is floored to one. Deliveries beyond as-of remain open with zero delivered quantity and amount. Their unobserved future delivery is not exported.
9. **Targets:** Planner noise is sampled before daily simulation. Target values depend only on prior-year SI and configured growth/noise. Q4 2026 targets exist while Q4 2026 actuals do not.

## Edge cases fixed for later KPI milestones

- C09: if either period has zero quantity, ASP and the two-factor decomposition are undefined. Report NULL components and an explicit undecomposed amount/residual; never drop those SKUs silently and claim full delta reconciliation. In the positive-quantity cohort, exact Decimal/NUMERIC decomposition must sum to delta amount.
- P01/B2: return NULL with a reason if no retailer is promotion-free throughout the matching window/pre-period or if the control baseline is zero. Calendar slots can overlap across retailers; report eligible promotion count and excluded cases rather than force a control.
- S10: the fraction `1 - zero_closing_days / panel_days` is multiplied by 100 when displayed as Availability %. Truth availability remains a validation measure, not an analytics input.
- R02/R03: evaluate only origins whose entire (t, t+7] label window is observed; the last seven days are right-censored and cannot be labelled negative by default.

## Suggestions from the supplied Claude/Gemini summary

| Suggestion | Decision / boundary |
| --- | --- |
| Retailer-specific promo slots | Implemented in config: start-day 12, 23, 5; months 2/6/10 (final year 2/6), preserving clean history/post periods |
| PRICE_DISCOUNT, BOGO, BANDED_PACK | PRICE_DISCOUNT only. Other mechanics require effective unit/pack price and fulfilment definitions; they are not interchangeable discount labels |
| Country of origin, import lead time, MOQ | Added as fictional descriptive product attributes. They do not drive the 2/3/2-day retailer delivery simulation |
| FCL constraints / upstream import planning | Deferred; requires supplier/container/DC inventory and purchase-order model, not just a product attribute |
| Store tiers | Added A/B/C; tier factors affect store demand size. All 10 SKUs remain in the complete panel in all 15 stores |
| Selective listing / promo targeting to some stores | Deferred; current contract explicitly applies a promo to all stores of one retailer-SKU |

## Milestones

M0: repository structure, pinned dependencies, scenario config, preserved/reviewed specifications and run commands.
M1: unified generator, CSV/manifest, DQ-01..17 local gate, PostgreSQL DDL/COPY snapshot loader, transactional replacement and optional integration checks.
M2: commercial/service calculations, SQL and Dashboard with independent reconciliation tests. Local CSV calculations can be verified while database integration is pending; SQL acceptance requires database parity tests.
M3: baselines and both specified backtests, cutoff leakage tests, forecast/outlook/gap — implemented locally; see M3_ACCEPTANCE.md.
M4: B1/B2 promotion estimators, censoring and truth-validation error reporting.
M5: observed availability/cover and held-out risk/lost-sales evaluation against truth.

The supplied drafts do not define exact M0..M5 acceptance plans beyond KPI milestone tags; this ordering is the explicit implementation plan here, not an invented quotation from an older chat. No RFM, ROI, margin or real-market claim is added.
