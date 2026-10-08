import csv
import datetime as dt
import tempfile
from pathlib import Path
import unittest
from fmcg.generate import ROOT, config_read, promotion_months
from fmcg.uplift.estimators import build
from fmcg.promotion_scenario import benchmark_summary, render_benchmark


class PromotionScenarioTests(unittest.TestCase):
    def test_default_calendar_falls_back_without_overrides(self):
        cfg, _, _ = config_read(ROOT / "config/scenario.toml")
        for cid in ("C01", "C02", "C03"):
            self.assertEqual(promotion_months(cfg, cid, False), [2, 6, 10])
            self.assertEqual(promotion_months(cfg, cid, True), [2, 6])

    def test_versioned_customer_calendar(self):
        cfg, _, _ = config_read(ROOT / "config/scenario_staggered_v1.toml")
        self.assertEqual(promotion_months(cfg, "C02", False), [3, 7, 11])
        self.assertEqual(promotion_months(cfg, "C03", True), [4, 8])
        self.assertEqual([c["promo_start_day"] for c in cfg["customers"]], [5, 15, 25])

    def test_invalid_calendar_fails_before_generation(self):
        original = (ROOT / "config/scenario_staggered_v1.toml").read_text()
        for edited in (original.replace("C01 = [2, 6, 10]", "C99 = [2, 6, 10]"),
                       original.replace("C01 = [2, 6, 10]", "C01 = [2, 2, 10]"),
                       original.replace("C01 = [2, 6, 10]", "C01 = [0, 6, 10]"),
                       original.replace("promo_start_day = 25", "promo_start_day = 31")):
            with tempfile.TemporaryDirectory() as tmp:
                config = Path(tmp) / "invalid.toml"; config.write_text(edited)
                with self.assertRaises(ValueError):
                    config_read(config)

    def fixture(self, root, contaminated):
        warehouse = root / "warehouse"; warehouse.mkdir()
        def write(name, fields, rows):
            with (warehouse / (name + ".csv")).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
        write("dim_store", ["store_id", "customer_id"],
              [dict(store_id=c+"S01", customer_id=c) for c in ("C01", "C02", "C03")])
        write("dim_product", ["product_id", "category"], [dict(product_id="P01", category="Coffee")])
        sales=[]; inventory=[]
        for day in range(180):
            date = str(dt.date(2026, 1, 1) + dt.timedelta(days=day))
            for cid in ("C01", "C02", "C03"):
                sales.append(dict(date=date, store_id=cid+"S01", product_id="P01", quantity=100))
                inventory.append(dict(date=date, store_id=cid+"S01", product_id="P01", closing_qty=100))
        write("fact_sales_daily", ["date", "store_id", "product_id", "quantity"], sales)
        write("fact_inventory_daily", ["date", "store_id", "product_id", "closing_qty"], inventory)
        promotions = [dict(promo_id="T", customer_id="C01", product_id="P01", start_date="2026-03-01", end_date="2026-03-07")]
        if contaminated:
            # Earlier promo ended Jan 25, but its post-dip lasts into the treated pre-period (Feb 1).
            promotions.append(dict(promo_id="C", customer_id="C02", product_id="P01", start_date="2026-01-19", end_date="2026-01-25"))
        write("dim_promotion", ["promo_id", "customer_id", "product_id", "start_date", "end_date"], promotions)

    def test_control_post_dip_contamination_is_excluded_without_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root, True)
            rows = build(root)
            result = next(r for r in rows if r["promo_id"] == "T" and r["method"] == "B2")
            self.assertEqual(result["control_customer_ids"], "C03")
            self.assertEqual(result["status"], "available")
            self.assertFalse((root / "truth").exists())

    def test_clean_controls_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root, False)
            result = next(r for r in build(root) if r["method"] == "B2")
            self.assertEqual(result["control_customer_ids"], "C02,C03")
            self.assertEqual(result["uplift_pct"], 0)

    def test_matched_count_excludes_unavailable_pair(self):
        rows=[dict(promo_id="A",method="B1",status="available"),
              dict(promo_id="B",method="B1",status="available"),
              dict(promo_id="A",method="B2",status="available"),
              dict(promo_id="B",method="B2",status="unavailable",reason="negative_daily_baseline")]
        result=benchmark_summary(rows, [], [])
        self.assertEqual(result["matched_promotions"], 1)
        self.assertEqual(result["available"]["B1"], 2)
        self.assertEqual(result["unavailable_reasons"]["B2"], {"negative_daily_baseline": 1})

    def test_benchmark_page_uses_run_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=dict(promotions=10,available=dict(B1=10,B2=9),matched_promotions=9,
                        matched_validation=[dict(method="B1",cohort="all",uplift_count=9,
                            uplift_bias_pp=1,uplift_mae_pp=2,post_dip_mae_pp=3)])
            render_benchmark(result, Path(tmp))
            page=(Path(tmp)/"benchmark.html").read_text()
            self.assertIn("10/10",page)
            self.assertIn("9/10",page)
            self.assertIn("../../index.html",page)
            self.assertNotIn("{b1}",page)


if __name__ == "__main__":
    unittest.main()
