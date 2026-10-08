"""Export authored Q4 SI scenarios without replacing the default M3 forecast."""
import argparse
import json
from html import escape
from .generate import ROOT, sha256
from .validate import validate
from .planning.bridge import build, load_plan
from .planning.cockpit import render as render_cockpit
from .promotion_report import encode, write_csv


def render(result, output):
    def money(value):
        return format(float(value)/100, ",.2f")
    summaries=[]
    for row in result["outlook"]:
        summaries.append("<tr><td>"+escape(row["scenario"])+"</td><td>"+escape(row["customer_id"])+
            "</td><td>"+money(row["baseline_gap_satang"])+"</td><td>"+money(row["additional_q4_si_satang"])+
            "</td><td>"+money(row["scenario_gap_satang"])+"</td></tr>")
    promotions=[]
    for row in result["promotions"]:
        promotions.append("<tr><td>"+escape(row["scenario"])+"</td><td>"+escape(row["product_name"])+
            "</td><td>"+row["expected_receipt_date"]+"</td><td>"+str(row["delivered_cases"])+
            "</td><td>"+format(float(row["unserved_positive_delta_so_units"]),".2f")+
            "</td><td>"+format(float(row["closing_delta_stock_units"]),".2f")+"</td></tr>")
    page="""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Q4 incremental SI plan</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#173045}
table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.wrap{overflow-x:auto}</style>
<h1>Q4 incremental Sale-In plan</h1><p>100% synthetic · Authored planning assumptions · As-of 2026-09-30</p>
<p><a href="cockpit.html">Monthly and order review</a> · <a href="../../index.html">Default demo</a> · <a href="../../m3/dashboard.html">Unchanged M3 outlook</a> · <a href="planning.json">Full assumptions and outputs</a></p>
<p>Historical B1 effects are transferred with an assumed 25% incremental share beyond the existing baseline.
This share is not an estimated causal correction. Scenarios are assumptions, not confidence intervals.</p>
<h2>Annual target gap (THB)</h2><div class="wrap"><table><thead><tr><th>Scenario</th><th>Retailer</th><th>Baseline gap</th>
<th>Additional Q4 SI</th><th>Scenario gap</th></tr></thead><tbody>SUMMARIES</tbody></table></div>
<h2>Incremental stock and delivery</h2><div class="wrap"><table><thead><tr><th>Scenario</th><th>SKU</th><th>Expected receipt</th>
<th>Delivered cases</th><th>Unserved positive delta units</th><th>Closing delta stock units</th></tr></thead><tbody>PROMOTIONS</tbody></table></div>
<p>Additional SI is recognised on assumed delivery dates at as-of invoice prices. A positive SI increment can increase retailer stock even when the extra consumer demand is not fulfilled; target attainment alone does not establish promotion profitability.</p>
<p>The stock ledger is incremental at retailer-SKU level. Baseline replenishment is assumed to maintain its reserved stock.
Case minimums/capacity are authored retail constraints, not import MOQ/FCL. Discounts are calendar descriptors; no discount-response elasticity, funding or margin model is estimated.</p>
<p>Q1 post-promotion spillover is tracked separately. Negative gap denotes a surplus. Read the assumptions before comparing scenarios.</p></html>"""
    (output/"benchmark.html").write_text(page.replace("SUMMARIES","".join(summaries)).replace("PROMOTIONS","".join(promotions)),encoding="utf-8")


def run():
    output=ROOT/"output/scenarios/q4-plan-v1";output.mkdir(parents=True,exist_ok=True)
    status=output/"planning_status.json";status.write_text('{"status":"running"}\n')
    try:
        data=ROOT/"data";config=ROOT/"config/scenario.toml";plan_path=ROOT/"config/q4_plan_v1.toml"
        quality,_=validate(data,config,strict_sanity=True)
        if quality["status"]!="passed":
            raise ValueError("Default scenario DQ failed; rebuild the default release first")
        plan=load_plan(plan_path);result=build(data,plan)
        for name in ("promotions","monthly","outlook"):
            write_csv(output/(name+".csv"),result[name])
        (output/"planning.json").write_text(json.dumps(encode(result),indent=2)+"\n")
        exact={}
        from fractions import Fraction
        for name in ("promotions","monthly","outlook"):
            exact[name]=[{k:dict(numerator=str(v.numerator),denominator=str(v.denominator)) for k,v in row.items()
                          if isinstance(v,Fraction)} for row in result[name]]
        (output/"rational_exact.json").write_text(json.dumps(exact,indent=2)+"\n")
        render(result,output)
        write_csv(output/"actions.csv",render_cockpit(result,output))
        summary=dict(status="passed",scenario="q4-plan-v1",source_manifest_sha256=sha256(data/"manifest.json"),
                     plan_sha256=sha256(plan_path),outlook=result["outlook"])
        status.write_text(json.dumps(encode(summary),indent=2)+"\n")
        return summary
    except Exception:
        status.write_text('{"status":"failed"}\n')
        raise


if __name__=="__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(encode(run()),indent=2))
