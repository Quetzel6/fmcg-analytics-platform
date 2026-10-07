# M2 coverage and acceptance

Implemented locally: C01–C10 and S01–S07. The as-of date comes from the data manifest; M2 requires month-end and refuses an as-of outside observed history. SQL views use the maximum loaded date dimension date.

| Definition | Verification |
| --- | --- |
| C01/C02 amounts and quantities | Exported YTD totals reconcile independently to daily SO and delivered SI source rows |
| C03/C04 growth | Matched LY month/YTD/quarter ranges; January MoM compares with previous December; zero denominator NULL |
| C05/C06/C07 | YTD source totals, exact contributions sum to 100 per retailer/type, dense tied ranks 1/1/2 |
| C08 | Fraction ASP; zero quantities return NULL |
| C09 | Exact rational price/volume sums equal delta amount; zero-quantity periods retain explicit undecomposed delta |
| C10 | Independently summed same-month YTD targets; annual target never used as denominator |
| S01–S05 | Hand-calculated cohort fixture includes early, late, short, open-overdue and future-promised lines |
| S06 | Mean and linearly interpolated P90 are exact fractions, matching the percentile-cont convention without floating arithmetic |
| S07 | Only as-of-open lines count; short-delivery remainders cancelled; overdue open subset tested |
| Historical cutoff | Later delivered amounts excluded; future deliveries appear open at earlier cutoffs |
| Export | Exact rational evidence retained; embedded script escaped |
| Dashboard | Actual JavaScript executed with a DOM harness; tables, SVG chart and all three filters verified |
| PostgreSQL parity | Optional test compares all four SQL views to local outputs; not executed without isolated database |

Calculation input is only `data/warehouse/` plus period metadata in manifest. Validation is orchestrated separately before export. No private validation dataset is read by the analytics package or SQL views.

`monthly.csv` is SKU/customer/type/month; `sku_ytd.csv` retains the customer/type denominator for contribution/rank; `category_ytd.csv` includes SI target attainment; `quarterly.csv` compares matching quarter months; `service.csv` includes each retailer and ALL. PostgreSQL percentages may use a different finite NUMERIC division precision than local rational representations; the optional parity test checks a small tolerance for ratios/effects while amount/quantity totals must match exactly.

Dashboard filters: category narrows commercial charts and tables but does not change contribution/rank partitions; service remains retailer-level; SO bridge stays SO even if the commercial toggle is SI. All boundaries are labelled in the page. Browser arithmetic is presentation only; exported money sums and business calculations are authoritative.

M2 is verified locally. PostgreSQL SQL execution, full database parity and runtime rollback remain pending because this environment has no PostgreSQL server. M3 forecast/outlook, M4 uplift and M5 availability/risk are not presented as completed.

Release result: 36 test cases, 34 passed, 2 skipped (PostgreSQL only). A singular-test summary parsing issue in the runner was corrected; audit notes identify unchanged test/production source and completed logs used for collection.
