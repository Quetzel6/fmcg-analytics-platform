"""Separate synthetic receipt-risk evaluation; the accepted M5 panel stays unchanged."""
import argparse
import json
from html import escape
from .generate import ROOT, generate, sha256
from .validate import validate
from .risk.receipts import build, load_policy
from .receipt_validation import evaluate
from .promotion_report import encode, write_csv


def render(result, output):
    table = []
    for row in encode(result["metrics"]):
        def percent(key):
            return "N/A" if row[key] is None else format(float(row[key]) * 100, ".2f") + "%"
        table.append("<tr><td>" + escape(row["method"]) + "</td><td>" + str(row["samples"]) +
                     "</td><td>" + percent("precision") + "</td><td>" + percent("recall") +
                     "</td><td>" + ("N/A" if row["pr_auc"] is None else format(float(row["pr_auc"]), ".4f")) + "</td><td>" + str(row["fp"]) + "</td></tr>")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Receipt risk benchmark</title><style>body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:0 20px;color:#173045}
table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}.wrap{overflow-x:auto}</style>
<h1>Receipt-aware risk · reserved 2027</h1><p>100% synthetic · Evaluation: 2027-01-01 to 2027-09-23 · 7-day lost-demand label</p>
<p><a href="../../index.html">Default demo</a> · <a href="benchmark_status.json">Full metrics and protocol</a> · <a href="latest_risk.csv">Latest predictions</a></p>
<div class="wrap"><table><thead><tr><th>Method</th><th>Matched N</th><th>Precision</th><th>Recall</th><th>PR-AUC</th><th>False positives</th></tr></thead><tbody>ROWS</tbody></table></div>
<p>Fixed policy: 80% of ordered units credited on a future promised date within 7 days.
Overdue promises are not credited. Each daily projected closing balance is checked, so a late receipt cannot hide earlier shortages.</p>
<p>More expected receipts can reduce alerts and false positives, but may also miss genuine shortages.
Promised deliveries can be delayed or short. This is a screening benchmark, not an automatic ordering policy.</p>
<p>The methods use the same evaluated rows. Future outcomes are used only to evaluate predictions.
The default 2026 M5 results, M3 outlook and dataset are not replaced.</p></html>"""
    (output / "benchmark.html").write_text(page.replace("ROWS", "".join(table)), encoding="utf-8")


def run():
    config = ROOT / "config/scenario_receipts_v1.toml"
    policy_path = ROOT / "config/receipt_risk_v1.toml"
    data = ROOT / "data/scenarios/receipts-v1"
    output = ROOT / "output/scenarios/receipts-v1"
    output.mkdir(parents=True, exist_ok=True)
    status = output / "benchmark_status.json"
    status.write_text('{"status":"running","scenario":"receipts-v1"}\n')
    try:
        policy = load_policy(policy_path)
        manifest = generate(config, data)
        quality, _ = validate(data, config, strict_sanity=True)
        (output / "data_quality.json").write_text(json.dumps(quality, indent=2) + "\n")
        if quality["status"] != "passed":
            raise ValueError("Receipt scenario failed strict DQ")
        import datetime as dt
        rows = build(data, dt.date.fromisoformat(manifest["as_of_date"]), policy)
        # Evaluation is called only after the observed feature panel is completed.
        metrics = evaluate(data, rows, policy)
        latest = [r for r in rows if r["date"] == manifest["as_of_date"]]
        write_csv(output / "risk_validation.csv", metrics)
        write_csv(output / "latest_risk.csv", latest)
        result = dict(status="passed", scenario="receipts-v1", policy=policy,
                      as_of_date=manifest["as_of_date"], rows=len(rows), metrics=metrics,
                      config_sha256=manifest["config_sha256"], generator_sha256=manifest["generator_sha256"],
                      policy_sha256=sha256(policy_path))
        render(result, output)
        status.write_text(json.dumps(encode(result), indent=2) + "\n")
        return result
    except Exception:
        status.write_text('{"status":"failed","scenario":"receipts-v1"}\n')
        raise


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(encode(run()), indent=2))
