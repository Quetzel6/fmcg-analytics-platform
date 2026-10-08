"""Supplemental M4 benchmark. Default data and M3 outlook are not replaced."""
import argparse
from collections import Counter
import datetime as dt
import json
from html import escape
from pathlib import Path

from .generate import ROOT, generate
from .validate import validate
from .uplift.estimators import build
from .promotion_validation import evaluate
from .promotion_report import encode, export
from .promotion_dashboard import render


def benchmark_summary(rows, all_validation, matched_validation):
    available = {method: sum(r["method"] == method and r["status"] == "available" for r in rows)
                 for method in ("B1", "B2")}
    paired = {r["promo_id"] for r in rows if r["method"] == "B1" and r["status"] == "available"} & {
        r["promo_id"] for r in rows if r["method"] == "B2" and r["status"] == "available"}
    return {
        "status": "passed",
        "scenario": "staggered-v1",
        "promotions": len({r["promo_id"] for r in rows}),
        "available": available,
        "matched_promotions": len(paired),
        "unavailable_reasons": {
            method: dict(Counter(r["reason"] for r in rows if r["method"] == method and r["status"] != "available"))
            for method in ("B1", "B2")},
        "all_available_validation": all_validation,
        "matched_validation": matched_validation,
        "interpretation": "Calendar eligibility is not a parallel-trends guarantee. Compare matched cohorts; neither method is presumed better.",
    }


def render_benchmark(result, output):
    cells = []
    for row in encode(result["matched_validation"]):
        if row["cohort"] != "all":
            continue
        def number(key):
            value = row[key]
            return "N/A" if value is None else format(float(value), ".2f")
        cells.append("<tr><td>" + escape(row["method"]) + "</td><td>" + str(row["uplift_count"]) +
                     "</td><td>" + number("uplift_bias_pp") + "</td><td>" + number("uplift_mae_pp") +
                     "</td><td>" + number("post_dip_mae_pp") + "</td></tr>")
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Staggered promotion benchmark</title><style>
body{font:16px system-ui;margin:32px auto;padding:0 20px;max-width:900px;color:#152b3c}
table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}
.wrap{overflow-x:auto}a{color:#176987}</style><h1>Staggered promotion benchmark</h1>
<p>100% synthetic · Scenario staggered-v1 · As-of 2026-09-30</p>
<p><a href="dashboard.html">Open promotion dashboard</a> · <a href="../../index.html">Default demo</a></p>
<p>B1 available: {b1}/240 · B2 available: {b2}/240 · Matched comparison: {matched} promotions.</p>
<div class="wrap"><table><thead><tr><th>Method</th><th>Matched N</th><th>Uplift Bias (pp)</th>
<th>Uplift MAE (pp)</th><th>Post-dip MAE (pp)</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Lower MAE is better. Both methods are compared on the same available promotions.
One B2 estimate is unavailable due to a negative daily baseline; it is excluded from both matched results.</p>
<p>Calendar eligibility does not establish parallel trends. Stockouts, retailer differences and seasonality
can affect estimates. Planted effects are used only for validation. The default M3 outlook is unchanged.</p>
<p>Full all/uncensored cohorts and fingerprints: <a href="benchmark_status.json">benchmark status</a>.</p></html>"""
    # Keep denominator and unavailable counts derived from the current run.
    page = page.replace("/240", "/" + str(result["promotions"]))
    unavailable = result["promotions"] - result["available"]["B2"]
    page = page.replace("One B2 estimate is unavailable due to a negative daily baseline",
                        str(unavailable) + " B2 estimates are unavailable (see status JSON for reasons)")
    (output / "benchmark.html").write_text(
        page.replace("{b1}", str(result["available"]["B1"])).replace("{b2}", str(result["available"]["B2"])).replace("{matched}", str(result["matched_promotions"])).replace("{rows}", "".join(cells)), encoding="utf-8")


def run():
    config = ROOT / "config/scenario_staggered_v1.toml"
    data = ROOT / "data/scenarios/staggered-v1"
    output = ROOT / "output/scenarios/staggered-v1"
    output.mkdir(parents=True, exist_ok=True)
    status_path = output / "benchmark_status.json"
    status_path.write_text(json.dumps({"status": "running", "scenario": "staggered-v1"}) + "\n")
    try:
        manifest = generate(config, data)
        quality, _ = validate(data, config, strict_sanity=True)
        (output / "data_quality.json").write_text(json.dumps(quality, indent=2) + "\n")
        if quality["status"] != "passed":
            raise ValueError("Supplemental scenario failed strict DQ")
        # Observed estimates are completed before isolated planted-effect validation.
        rows = build(data, dt.date.fromisoformat(manifest["as_of_date"]))
        errors, all_validation = evaluate(data, rows)
        paired = {r["promo_id"] for r in rows if r["method"] == "B1" and r["status"] == "available"} & {
            r["promo_id"] for r in rows if r["method"] == "B2" and r["status"] == "available"}
        if not paired:
            raise ValueError("No matched B1/B2 promotions; supplemental benchmark is unavailable")
        _, matched_validation = evaluate(data, [r for r in rows if r["promo_id"] in paired])
        export(rows, errors, all_validation, output)
        render(output / "promotion.json", ROOT / "dashboard/m4.html", output / "dashboard.html")
        dashboard = output / "dashboard.html"
        page = dashboard.read_text().replace('../m2/dashboard.html', '../../m2/dashboard.html').replace('../m3/dashboard.html', '../../m3/dashboard.html').replace('../m5/dashboard.html', '../../m5/dashboard.html')
        page = page.replace('<h1>Promotion effectiveness · M4</h1>', '<h1>Promotion effectiveness · staggered-v1</h1><p><a href="benchmark.html">Matched B1/B2 benchmark</a></p>')
        dashboard.write_text(page, encoding="utf-8")
        result = benchmark_summary(rows, all_validation, matched_validation)
        result["config_sha256"] = manifest["config_sha256"]
        result["generator_sha256"] = manifest["generator_sha256"]
        result["as_of_date"] = manifest["as_of_date"]
        render_benchmark(result, output)
        status_path.write_text(json.dumps(encode(result), indent=2) + "\n")
        return result
    except (ValueError, OSError):
        status_path.write_text(json.dumps({"status": "failed", "scenario": "staggered-v1"}) + "\n")
        raise


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run()
    print(json.dumps(encode(result), indent=2))
