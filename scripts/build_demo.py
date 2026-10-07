"""Build a compact offline project entry page from current report artifacts."""
import csv
import html
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    output=ROOT/'output';risk=json.loads((output/'m5/risk.json').read_text())
    with (output/'m3/outlook_summary.csv').open(newline='') as stream:outlook=next(r for r in csv.DictReader(stream) if r['customer_id']=='ALL')
    metrics=next(r for r in risk['risk_validation'] if r['cohort']=='heldout_2026_matched' and r['method']=='weekday_uncensored_cover')
    cards=[('M2 · Commercial & service','m2/dashboard.html','ยอดขาย SI/SO, SKU contribution, Target และ OTIF'),('M3 · Forecast & closing plan','m3/dashboard.html','Backtest สองช่วง, เลือก baseline และ Gap รายห้าง'),('M4 · Promotion effectiveness','m4/dashboard.html','Uplift / Post-Promo Dip / Net Uplift พร้อม stockout cohorts'),('M5 · Inventory & risk','m5/dashboard.html','Days of Cover, Availability, Risk และ Lost Sales validation')]
    links=''.join('<a class="panel" href="'+href+'"><h2>'+html.escape(title)+'</h2><p>'+html.escape(text)+'</p><strong>เปิด Dashboard →</strong></a>' for title,href,text in cards)
    page='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FMCG Analytics · Demo</title><style>body{margin:0;background:#eef3f7;color:#193248;font:16px system-ui}main{max-width:1080px;margin:auto;padding:36px}h1{font-size:34px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}.panel{display:block;background:white;padding:24px;border-radius:14px;color:inherit;text-decoration:none;border:1px solid #dce6ee}.panel:hover{border-color:#147d89}p,li{line-height:1.7}.notice{background:#fff0c7;border-radius:12px;padding:20px;margin:24px 0}strong{color:#147d89}</style><main><p>DATA ENGINEERING & ANALYTICS PORTFOLIO</p><h1>FMCG Commercial & Supply Chain Analytics</h1><p>100% Synthetic Data · As of 2026-09-30 · Offline demo</p><div class="grid">'''+links+'''</div><div class="notice"><h2>ผลที่ตรวจสอบได้และขอบเขต</h2><ul><li>Gap รวมจาก M3: ฿'''+f"{float(outlook['gap_to_annual_target_satang'])/100:,.2f}"+''' · เงินต้นทางใช้หน่วยสตางค์</li><li>M4 B1 ครบ 240 โปรโมชัน; B2 ไม่มี clean control ในตารางโปรโมชันชุดนี้</li><li>M5 held-out matched: Precision '''+f"{float(metrics['precision'])*100:.2f}%"+''' / Recall '''+f"{float(metrics['recall'])*100:.2f}%"+''' · ยังแจ้งเตือนเกินมาก</li><li>PostgreSQL integration ยังไม่ได้ยืนยันในสภาพแวดล้อมนี้</li></ul></div><p>เส้นทางดู Demo: M2 → M3 → M4 → M5 · ดูรายละเอียดวิธีและผลทดสอบใน README และ docs/</p></main></html>'''
    target=output/'index.html';target.write_text(page);return target
if __name__=='__main__':print(build())
