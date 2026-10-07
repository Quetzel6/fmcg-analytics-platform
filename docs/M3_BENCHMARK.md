# Default synthetic M3 benchmark

As-of: 2026-09-30. Synthetic scenario only; definitions and protocol: M3_ACCEPTANCE.md and KPI_DICTIONARY.md. Values below come from output/m3/backtest_scores.csv; percentages rounded to two decimals for display.

| Origin → horizon | Method | WAPE % | Bias % |
| --- | --- | ---: | ---: |
| 2025-09-30 → Q4 2025 | seasonal_naive | 10.01 | -7.45 |
| 2025-09-30 → Q4 2025 | ly_ytd_growth | 5.82 | 0.92 |
| 2025-09-30 → Q4 2025 | seasonal_run_rate | 7.39 | -1.22 |
| 2026-06-30 → Q3 2026 | seasonal_naive | 10.23 | -8.27 |
| 2026-06-30 → Q3 2026 | ly_ytd_growth | 5.90 | 0.07 |
| 2026-06-30 → Q3 2026 | seasonal_run_rate | 6.95 | 1.67 |

Selected: `ly_ytd_growth` under the fixed two-origin rule. Each row evaluates 36 points; no incomplete predictions in the default scenario. Lower historical WAPE here does not imply real-business accuracy.

Source manifest SHA-256: `6c6eabc8b4beb2d49dd81aa536e24e266baa67ebc07c05b4a8cbc20a75ffe0e3`.
