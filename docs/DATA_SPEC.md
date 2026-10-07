# Data Specification — FMCG Commercial & Supply Chain Analytics

**Status:** Reviewed working contract v0.2. M0 and local M1 are implemented; PostgreSQL integration acceptance is pending. See IMPLEMENTATION_STATUS.md and REVIEW_NOTES.md. Original v0.1 is preserved in source_specs/.
**Data class:** 100% synthetic. No real company, retailer, brand or price is represented.

## 1. Purpose

This specification defines the synthetic dataset, the star schema, the generation model, the ground truth kept for validation, and the data-quality rules. Every KPI in `KPI_DICTIONARY.md` must be computable from the tables defined here, and every number in the README must trace back to this document and to code that is covered by a test.

Parameter values marked *(initial)* are design choices, not recovered requirements. They live in `config/scenario.toml` and may be tuned; the structure is what this document fixes.

## 2. Scenario scope

| Item | Value |
|---|---|
| Period | 2024-01-01 to 2026-09-30 (1,004 days: 366 + 365 + 273) |
| As-of date | 2026-09-30. Q4 2026 is the forecast horizon; Q4 2025 is the backtest window |
| Retailers (customers) | 3: Modern Trade, Wholesale, Supermarket |
| Stores | 15 (5 per retailer) |
| SKUs | 10 across 4 categories |
| Daily panel size | 1,004 days × 15 stores × 10 SKUs = **150,600 rows** for sales and for inventory |
| Currency | Thai baht, stored as integer satang |
| Why start in 2024 | A Q4 2025 backtest needs one prior year of seasonal history. Starting in 2025 would make the backtest impossible |

### Products *(initial; fictional brands)*

| ID | Product | Brand | Category | 2024 shelf price (฿) | Case size |
|---|---|---|---|---|---|
| P01 | Gold Coffee Jar 200g | Aurora | Coffee | 229 | 12 |
| P02 | Classic Coffee Jar 200g | Aurora | Coffee | 199 | 12 |
| P03 | 3-in-1 Coffee Sachet ×20 | Aurora | Coffee | 129 | 12 |
| P04 | Sardines Tomato 155g | Harbor | Canned Fish | 35 | 24 |
| P05 | Tuna Brine 165g | Harbor | Canned Fish | 45 | 24 |
| P06 | Fresh Toothpaste 150g | Smile | Oral Care | 69 | 24 |
| P07 | Mint Toothpaste 100g | Smile | Oral Care | 49 | 24 |
| P08 | Chocolate Wafer 30g | Cocoa | Snacks | 12 | 48 |
| P09 | Chocolate Bar 40g | Cocoa | Snacks | 19 | 48 |
| P10 | Potato Crisps 50g | Crispa | Snacks | 25 | 48 |

## 3. Star schema

```
                       dim_date
                          │
dim_customer ── dim_store ┼── fact_sales_daily ── dim_product ── dim_price
      │                   ├── fact_inventory_daily     │
      │                   └── fact_order_line ─────────┤
      ├── dim_promotion ───────────────────────────────┘
      └── fact_target_monthly (customer × category × month)
```

Logical schema `fmcg`. Money is `BIGINT` satang; quantities are `BIGINT` pieces; dates are `DATE`.

### Dimensions

| Table | Grain / PK | Columns |
|---|---|---|
| `dim_date` | one row per date | `date_key`, `year`, `quarter`, `month`, `month_start`, `iso_week`, `day_of_week` (1=Mon), `is_weekend` |
| `dim_customer` | `customer_id` | `customer_name`, `channel` |
| `dim_store` | `store_id` | `customer_id` FK, `store_name`, `region` (BKK, Central, North, Northeast, South), `format` |
| `dim_product` | `product_id` | `product_name`, `brand`, `category`, `case_size` |
| `dim_price` | `product_id` × `effective_from` | `shelf_price_satang`, `invoice_price_satang`. One version per year; annual list-price change of 0–4% *(initial)* on 1 Jan 2025 and 2026. Invoice price = 80% of shelf price *(initial)* |
| `dim_promotion` | `promo_id` | `customer_id`, `product_id`, `start_date`, `end_date`, `discount_pct` (10/15/20/25/30), `mechanic` (= `PRICE_DISCOUNT`) |

A promotion applies to all stores of one retailer for one SKU. The markdown is retailer-funded: it lowers the shelf price but not the invoice price, so Sale-In prices are unaffected by promotions. (Consequence: no promotion cost exists in the data, so no promotion ROI is computed.)

### Facts

| Table | Grain / PK | Columns | Meaning |
|---|---|---|---|
| `fact_sales_daily` | `date × store_id × product_id` | `quantity`, `unit_price_satang`, `amount_satang` | **Sell-Out (SO)**: consumer sales at the store. Complete panel; zero sales are explicit zero rows. `amount = quantity × unit_price` exactly |
| `fact_inventory_daily` | `date × store_id × product_id` | `opening_qty`, `receipt_qty`, `sold_qty`, `adjustment_qty`, `closing_qty` | End-of-day stock ledger. `closing = opening + receipt − sold + adjustment`. `adjustment` is signed (shrink / count corrections) |
| `fact_order_line` | `order_id × line_id` | `store_id`, `product_id`, `order_date`, `promised_date`, `delivered_date` (NULL if not yet delivered), `ordered_qty`, `delivered_qty`, `unit_price_satang`, `amount_satang` | Replenishment orders to the distributor. One order = one store on one day; one line = one SKU. Single delivery event per line. **Sale-In (SI)** = `delivered_qty × invoice price`, recognised on `delivered_date` |
| `fact_target_monthly` | `month_start × customer_id × category` | `target_amount_satang` | Sale-In sales target, set before the year starts from prior-year SI × planned growth, with planner noise. Covers 2025 and 2026 (full years, including Q4) |

Order-line rules: `delivered_date IS NULL ⇔ delivered_qty = 0` (still open). `0 < delivered_qty < ordered_qty` is a short shipment and the remainder is cancelled (no backorder). A delivery that would fall after the as-of date is stored as open.

Sale-In and Sell-Out are linked by one simulation: `receipt_qty` in the ledger equals `delivered_qty` by `delivered_date`, and `sold_qty` equals SO `quantity`. There is no "net inflow" proxy for stock; stock is an explicit ledger.

## 4. Generation model

All randomness comes from one seeded `numpy.random.Generator(PCG64)`.

**Step 1 — latent demand.** For each date × store × SKU:

`λ = base_rate × seasonality[category, month] × weekday[channel, dow] × trend[customer, t] × promo_effect × noise`

- `base_rate`: category rate × store size factor (lognormal, clipped to 0.6–1.6) × SKU popularity.
- `seasonality`: category-specific monthly index; December peaks at 1.20–1.45 depending on category *(initial)*; secondary April peak for Coffee and Snacks.
- `weekday`: Modern Trade and Supermarket ×1.2 on weekends; Wholesale ×0.85 *(initial)*.
- `trend`: continuous annual growth per retailer, e.g. +6%, −3%, +12% *(initial)*.
- `promo_effect`: during a promotion, `1 + k_category × discount_pct/100 × lognormal(σ=0.2)`. For 14 days after a promotion, `1 − 0.25 × realised_uplift` (pull-forward dip). `k`: Coffee 2.0, Canned Fish 1.5, Oral Care 1.2, Snacks 2.5 *(initial)*.
- `noise`: gamma-mixed Poisson (overdispersed).

Promotion calendar: about 2–3 promotions per retailer-SKU per year (target 150–250 in total; exact count in the manifest), 7–14 days long, with at least 45 days between the end of one and the start of the next on the same retailer-SKU, so each promotion has a clean 28-day pre-period and post-period. *(Real calendars are denser; a dense-calendar stress scenario is a possible later extension.)*

**Step 2 — constrained sales.** `sold = min(latent_demand, opening + receipts)`. `lost = latent_demand − sold`. Lost sales are recorded in the truth schema only. The warehouse sees `sold`, which understates demand whenever stock runs out.

**Step 3 — retailer replenishment policy (uses observed sales only, like a real planner).** Each day per store × SKU:
`d̂` = mean and `σ̂` = std of `sold` over the last 14 days; `L` = standard lead time (2, 3, 2 days for the three retailers *(initial)*).
`ROP = d̂·(L+1) + 1.28·σ̂·√(L+1)`; order when `closing + open_order_qty ≤ ROP`; order-up-to level `S = ROP + 5·d̂`; quantity rounded up to whole cases.

**Step 4 — delivery.** `promised_date = order_date + L`. Delay (days) drawn from {−1: 4%, 0: 81%, +1: 9%, +2: 4%, +3: 2%} *(initial)* → about 85% on time. In-full probability about 93%; otherwise 60–95% of the quantity is delivered.

**Step 5 — supply disruptions.** Planted windows per retailer-SKU (target ≥ 20 events, 5–14 days): orders placed inside a window get +4 to +9 extra days of delay and 0–50% fill. These, plus promo spikes and ordinary replenishment lag, produce stockouts.

**Step 6 — adjustments.** Small random shrink (≈0.1% of stock-days), never taking stock below zero.

**Step 7 — targets.** `target = prior-year SI × (1 + planned growth) × uniform(0.97, 1.03)`, by retailer, category and month. Targets are not derived from the current year's actuals.

Opening stock on 2024-01-01 is `round(10 × base daily rate)`.

## 5. Ground truth (`truth` schema)

Kept outside the analytics layer. It exists only so later milestones can check whether a method recovers what was planted.

| Table | Content |
|---|---|
| `truth_demand_daily` | `date, store_id, product_id, baseline_demand_qty` (no promo effect, no stock limit), `latent_demand_qty`, `lost_qty` |
| `truth_promo_effect` | `promo_id, true_uplift_pct, true_post_dip_pct` |
| `truth_supply_disruption` | `event_id, customer_id, product_id, start_date, end_date, extra_delay_days, fill_factor` |

**Rule (tested):** no SQL or Python in the analytics, forecast, uplift or risk code may reference the `truth` schema. Only validation code may.

**Claim boundary:** because the effects are planted, a result such as "uplift estimated within X points of the true value" proves that the *method* works on this scenario. It does not prove anything about a real business.

## 6. Data-quality rules

Severity ERROR aborts the load and rolls back. WARN is reported.

| ID | Rule | Severity |
|---|---|---|
| DQ-01 | Primary keys unique; no nulls in key or measure columns (except `delivered_date`) | ERROR |
| DQ-02 | All foreign keys resolve | ERROR |
| DQ-03 | Quantities ≥ 0; only `adjustment_qty` may be negative | ERROR |
| DQ-04 | Observed dates within period; no actual after as-of. Future promised dates and full-year target months are allowed planning dates | ERROR |
| DQ-05 | Sales and inventory panels complete: every date × store × SKU present | ERROR |
| DQ-06 | `amount_satang = quantity × unit_price_satang` exactly | ERROR |
| DQ-07 | Realised SO price equals the effective shelf price, or the discounted price when a promotion is active | ERROR |
| DQ-08 | Ledger identity: `closing = opening + receipt − sold + adjustment`, `closing ≥ 0` | ERROR |
| DQ-09 | Opening continuity: next-day opening = prior-day closing | ERROR |
| DQ-10 | `inventory.sold_qty = sales.quantity` for every key | ERROR |
| DQ-11 | Receipts reconcile: ledger `receipt_qty` = Σ `delivered_qty` by `delivered_date`, store, SKU | ERROR |
| DQ-12 | Order dates: `order_date ≤ promised_date`; `order_date ≤ delivered_date ≤ as-of`; `delivered_qty ≤ ordered_qty`; open ⇔ zero delivered | ERROR |
| DQ-13 | Promotions: valid dates, no overlap on the same retailer-SKU | ERROR |
| DQ-14 | Every date has exactly one effective price version per SKU | ERROR |
| DQ-15 | Targets cover every month × retailer × category for 2025–2026 | ERROR |
| DQ-16 | After loading, row counts in PostgreSQL equal the manifest counts, and Σ amounts equal the CSV totals | ERROR |
| DQ-17 | Scenario sanity (see §8) | WARN in loader, ERROR in tests |

## 7. Reproducibility

- `config/scenario.toml` holds the seed and every *(initial)* parameter.
- Each run writes `manifest.json`: seed, config hash, `numpy` version, row counts, SHA-256 of each CSV.
- Same seed + same config + same generator code + same pinned `numpy` version ⇒ identical checksums (tested). A different `numpy` version may change the random stream; the dependency is pinned for that reason.
- Loading replaces the `fmcg` and `truth` schemas in one transaction; a failed load leaves the previous state untouched; a repeated load does not duplicate rows.

## 8. Scenario sanity bounds (tested)

The scenario must not be vacuous. Bounds *(initial)*:

- Store-SKU-days with `lost_qty > 0`: between 1% and 8%, and at least one stockout in every category.
- Line OTIF (as-of, due lines): between 70% and 92%.
- Every promotion has `true_uplift_pct > 0`; at least 20 disruption events.
- December index exceeds the Q1 mean index in every category.

## 9. Simplifications (out of scope)

Sales returns and negative transactions; multi-shipment or back-ordered lines; order cancellations by the retailer; substitution; batches and expiry; stock transfers; cost, margin and promotion funding (hence no ROI, no inventory valuation); cannibalisation and halo effects; competitor, weather and macro drivers; e-commerce; customer-level transactions (hence **no RFM or customer segmentation**: the data is store-SKU-day aggregates, not baskets or loyalty records).

## 10. What this data can and cannot support

| Can support | Cannot support |
|---|---|
| Demonstrating correct KPI definitions and SQL on a realistic structure | Any statement about real market behaviour or business impact |
| Showing a method recovers planted effects (uplift, stockout risk) | "We found that promotions in category X deliver Y%" as a business finding |
| Forecast backtests measured against held-out synthetic actuals | Claims that the forecast would be accurate on real data |
| Data-quality gating and reconciliation engineering | Claims about production scale or performance (≈150k rows per table) |

Planned answer to "is this real data?": *No. It is a generated scenario with known planted effects, built so that the analysis methods can be validated against ground truth. The value is the pipeline, the definitions and the validation, not the numbers.*

## 11. Changes from the earlier agreement

- Period extended from 2025–Sep 2026 to **2024–Sep 2026** so the Q4 2025 backtest has a prior-year baseline (≈95,700 → 150,600 daily rows).
- Sale-In is derived from delivered order lines, not generated as an independent monthly series.
- Orders are one per store per day with multiple lines, so Order OTIF is distinct from Line OTIF.
- `numpy` becomes a dependency (previous phase was standard-library only).

## 12. Reviewed implementation decisions (v0.2)

- Product attributes country_of_origin, import_lead_days and moq_cases are descriptive only; upstream import/FCL simulation is not implemented. Store tier and size_factor are explicit dimensions; tier factors affect demand.
- Prices use Decimal ROUND_HALF_UP to integer satang; amounts use exact integer multiplication.
- The first 14 planner days use a configured base-rate floor; thereafter only observed sold history is used.
- Each promotion has one sampled, planted demand multiplier and a capped post dip. Truth percentages refer to that multiplier, not the realised observed sales ratio.
- Positive observed deliveries are at least one piece; short-shipped remainders close as cancelled. Future deliveries export NULL date, zero quantity and amount.
- Scenario stats live in QA reports. DQ-16 database reconciliation is not claimed verified until PostgreSQL integration runs.
- All implemented deviations and decisions are detailed in REVIEW_NOTES.md.
