"""Offline review of the Q4 ledger; no new forecasts or target allocations."""
from decimal import Decimal, localcontext
from fractions import Fraction
from html import escape


def money(value):
    value = Fraction(value)
    with localcontext() as context:
        context.prec = max(50, len(str(abs(value.numerator))) + 10)
        return format(Decimal(value.numerator) / Decimal(value.denominator) / 100, ',.2f')


def actions(result):
    names = {r['customer_id']: r['customer_name'] for r in result['baseline_outlook']}
    rows = []
    for row in result['promotions']:
        flags = []
        if row['capacity_limited']:
            flags.append('Capacity limited')
        if row['unserved_positive_delta_so_units'] > 0:
            flags.append('Unserved incremental SO')
        if row['additional_q1_si_satang'] > 0:
            flags.append('Receipt in Q1')
        if row['post_end_date'][:4] == '2027':
            flags.append('Post period crosses into Q1')
        if row['closing_delta_stock_units'] > 0:
            flags.append('Residual incremental stock')
        rows.append(dict(scenario=row['scenario'], customer_id=row['customer_id'],
            customer_name=names[row['customer_id']], category=row['category'],
            product_id=row['product_id'], product_name=row['product_name'], promo_id=row['promo_id'],
            planning_state='Planned order' if row['delivered_cases'] else 'No incremental order',
            order_date=row['order_date'] if row['delivered_cases'] else '',
            expected_receipt_date=row['expected_receipt_date'] if row['delivered_cases'] else '',
            requested_order_cases=row['requested_order_cases'], delivered_cases=row['delivered_cases'],
            additional_delivered_si_units=row['additional_delivered_si_units'],
            additional_q4_si_satang=row['additional_q4_si_satang'],
            additional_q1_si_satang=row['additional_q1_si_satang'],
            unserved_positive_delta_so_units=row['unserved_positive_delta_so_units'],
            closing_delta_stock_units=row['closing_delta_stock_units'],
            review_flags='; '.join(flags) or 'No modeled exception'))
    return rows


def validate(result):
    """Check identities and grouping before publishing the presentation."""
    seen = set()
    for row in result['monthly']:
        key = tuple(row[k] for k in ('scenario', 'customer_id', 'category', 'year', 'month'))
        if key in seen or row['baseline_si_satang'] + row['additional_si_satang'] != row['scenario_si_satang']:
            raise ValueError('Duplicate or inconsistent monthly bridge')
        seen.add(key)
    for row in result['outlook']:
        same = lambda r: r['scenario'] == row['scenario'] and (row['customer_id'] == 'ALL' or r['customer_id'] == row['customer_id'])
        monthly = sum((r['additional_si_satang'] for r in result['monthly'] if same(r) and r['year'] == 2026), Fraction())
        deliveries = sum((r['additional_q4_si_satang'] for r in result['promotions'] if same(r)), Fraction())
        if monthly != deliveries or monthly != row['additional_q4_si_satang']:
            raise ValueError('Monthly/delivery/annual increment does not reconcile')
        if row['scenario_full_year_satang'] + row['scenario_gap_satang'] != row['annual_target_satang']:
            raise ValueError('Annual target does not reconcile')


def render(result, output):
    validate(result)
    action_rows = actions(result)
    names = {r['customer_id']: r['customer_name'] for r in result['baseline_outlook']}
    def e(value):
        return escape(str(value), quote=True)
    def cells(values):
        return ''.join('<td>'+e(v)+'</td>' for v in values)
    def attrs(row):
        return ' data-scenario="'+e(row['scenario'])+'" data-customer="'+e(row['customer_id'])+'" data-category="'+e(row.get('category', 'ALL'))+'"'
    def options(values):
        return ''.join('<option value="'+e(key)+'">'+e(label)+'</option>' for key, label in values)
    annual = ''.join('<tr'+attrs(r)+'>'+cells([names[r['customer_id']], money(r['annual_target_satang']),
        money(r['baseline_full_year_satang']), money(r['additional_q4_si_satang']),
        money(r['scenario_full_year_satang']), money(r['scenario_gap_satang'])])+'</tr>' for r in result['outlook'])
    monthly = ''.join('<tr'+attrs(r)+'>'+cells([names[r['customer_id']], r['category'],
        f"{r['year']}-{r['month']:02}", money(r['baseline_si_satang']), money(r['additional_si_satang']),
        money(r['scenario_si_satang'])])+'</tr>' for r in result['monthly'])
    orders = ''.join('<tr'+attrs(r)+'>'+cells([r['customer_name'], r['product_name'], r['category'],
        r['planning_state'], r['order_date'] or '—', r['expected_receipt_date'] or '—',
        r['requested_order_cases'], r['delivered_cases'], r['additional_delivered_si_units'],
        money(r['additional_q4_si_satang']), money(r['additional_q1_si_satang']),
        format(float(r['unserved_positive_delta_so_units']), '.2f'),
        format(float(r['closing_delta_stock_units']), '.2f'), r['review_flags']])+'</tr>' for r in action_rows)
    scenarios = options((s['name'], s['name']) for s in result['plan']['scenarios'])
    customers = options(names.items())
    categories = options([('ALL', 'All categories')]+[(c,c) for c in sorted({r['category'] for r in result['monthly']})])
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Q4 commercial review</title><style>
body{font:16px system-ui;color:#173045;background:#f5f7fa;margin:0}main{max-width:1280px;margin:auto;padding:24px}
section{background:white;padding:20px;margin:20px 0;border-radius:12px}h1{margin-bottom:8px}h2{font-size:22px}
.filters{display:flex;flex-wrap:wrap;gap:20px}label{display:grid;gap:6px}select{font:inherit;padding:8px;min-width:180px}
.wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:10px;border-bottom:1px solid #dde3ea;text-align:left;vertical-align:top}
th{background:#edf3f7}a{color:#075a8c}p{line-height:1.5}tr[hidden]{display:none}#scope{font-weight:600}
@media print{body{background:white}section{break-inside:avoid}.filters{display:none}.wrap{overflow:visible}table{font-size:10px}}
</style></head><body><main><h1>Q4 commercial review</h1>
<p>100% synthetic · As-of ASOF · Authored scenarios · Money in THB</p>
<p><a href="benchmark.html">Ledger and assumptions</a> · <a href="planning.json">Complete evidence</a> ·
<a href="monthly.csv">Monthly CSV</a> · <a href="actions.csv">Order review CSV</a> · <a href="../../index.html">Default demo</a></p>
<section class="filters"><label>Scenario<select id="scenario">SCENARIOS</select></label>
<label>Retailer<select id="customer">CUSTOMERS</select></label><label>Category<select id="category">CATEGORIES</select></label></section>
<p id="scope" role="status" aria-live="polite">All scenario rows shown until filters are enabled.</p>
<section><h2>Annual target bridge</h2><p>This section follows scenario and retailer only. The annual target is not allocated to categories or months. A negative gap denotes a surplus.</p>
<div class="wrap"><table id="annual"><thead><tr><th>Retailer</th><th>Annual target</th><th>Baseline outlook</th><th>Extra Q4 SI</th><th>Scenario outlook</th><th>Remaining gap</th></tr></thead><tbody>ANNUAL</tbody></table></div></section>
<section><h2>Monthly SI by category</h2><p>Forecast plus authored incremental receipts, not monthly sales targets. Categories without planned orders retain their baseline forecast.</p>
<div class="wrap"><table id="monthly"><thead><tr><th>Retailer</th><th>Category</th><th>Month</th><th>Baseline SI</th><th>Extra SI</th><th>Scenario SI</th></tr></thead><tbody>MONTHLY</tbody></table></div></section>
<section><h2>Incremental order review</h2><p>Planned quantities and expected dates are assumptions, not submitted orders or confirmed receipts. Requested cases may exceed capacity. Unserved quantities are lost incremental consumer demand; they are not backfilled.</p>
<div class="wrap"><table id="orders"><thead><tr><th>Retailer</th><th>SKU</th><th>Category</th><th>State</th><th>Order date</th><th>Expected receipt</th><th>Requested cases</th><th>Planned cases</th><th>SI units</th><th>Q4 SI</th><th>Q1 SI</th><th>Unserved SO units</th><th>Residual stock units</th><th>Review flags</th></tr></thead><tbody>ORDERS</tbody></table></div></section>
<section><h2>How to read this plan</h2><p>Historical B1 effects are transferred using an assumed 25% incremental share. The existing M3 forecast stays unchanged. These scenarios are not confidence intervals or evidence of improved forecast accuracy. Baseline replenishment is assumed to maintain reserved stock; the ledger is incremental at retailer-SKU level.</p>
<p>Extra Sell-In can remain in retailer inventory. Review capacity, unserved Sell-Out, residual stock and Q1 spillover together with the annual gap. Funding, GP, VAT and promotion ROI are not modeled. No automatic order submission takes place.</p></section>
<noscript><p>JavaScript is disabled: tables contain every scenario. Use the CSV scenario column to select one.</p></noscript>
</main><script>
const scenario=document.getElementById('scenario'), customer=document.getElementById('customer'), category=document.getElementById('category');
function update(){let monthlyCount=0,orderCount=0;
for(const id of ['annual','monthly','orders']) for(const row of document.querySelectorAll('#'+id+' tbody tr')){
 const customerMatches=id==='annual'?row.dataset.customer===customer.value:(customer.value==='ALL'||row.dataset.customer===customer.value);
 const categoryMatches=id==='annual'||category.value==='ALL'||row.dataset.category===category.value;
 row.hidden=!(row.dataset.scenario===scenario.value&&customerMatches&&categoryMatches);
 if(!row.hidden&&id==='monthly')monthlyCount++;if(!row.hidden&&id==='orders')orderCount++;
}
document.getElementById('scope').textContent=scenario.value+' · '+customer.selectedOptions[0].textContent+' · '+category.selectedOptions[0].textContent+' · '+monthlyCount+' monthly rows · '+orderCount+' order review rows';
}
for(const field of [scenario,customer,category])field.addEventListener('change',update);
if([...scenario.options].some(o=>o.value==='central'))scenario.value='central';update();
</script></body></html>'''
    replacements = dict(ASOF=e(result['as_of']), SCENARIOS=scenarios, CUSTOMERS=customers,
                        CATEGORIES=categories, ANNUAL=annual, MONTHLY=monthly, ORDERS=orders)
    # Substitute once so user-authored labels cannot become template tokens.
    import re
    page = re.sub('|'.join(replacements), lambda m: replacements[m.group()], page)
    (output/'cockpit.html').write_text(page, encoding='utf-8')
    return action_rows
