"""Incremental planning ledger over an unchanged M3 baseline."""
import datetime as dt
from fractions import Fraction
import math
import tomllib
from collections import defaultdict
from ..analytics.metrics import read
from ..uplift.estimators import build as promotion_estimates
from ..forecast.baselines import build as forecast

DAY = dt.timedelta(days=1)


def load_plan(path):
    with path.open("rb") as stream:
        plan = tomllib.load(stream)
    p = plan["planning"]
    if (p["as_of"], p["post_days"], p["effect_method"], p["effect_cohort"], p["invoice_price_policy"]) != (
            "2026-09-30", 14, "B1", "all_available", "hold_as_of_price"):
        raise ValueError("Unsupported Q4 v1 planning protocol")
    if not 0 <= Fraction(p["incrementality_fraction"]) <= 1:
        raise ValueError("Incrementality fraction must be between zero and one")
    for field in ("reserve_days", "lead_days", "minimum_order_cases"):
        if type(p[field]) is not int or p[field] < 1:
            raise ValueError("Invalid positive planning integer")
    seen = set(); ids = set()
    for row in plan["promotions"]:
        key = (row["customer_id"], row["product_id"])
        start = dt.date.fromisoformat(row["start_date"]); end = dt.date.fromisoformat(row["end_date"])
        if key in seen or row["id"] in ids:
            raise ValueError("Only one Q4 promotion per retailer-SKU is supported")
        seen.add(key); ids.add(row["id"])
        if not dt.date(2026,10,1) <= start <= end <= dt.date(2026,12,31) or start-p["lead_days"]*DAY <= dt.date(2026,9,30):
            raise ValueError("Q4 windows and order dates must lie after as-of")
        if row["mechanic"] != "PRICE_DISCOUNT" or type(row["discount_pct"]) is not int or not 0 < row["discount_pct"] < 100:
            raise ValueError("Invalid authored promotional mechanic")
        if type(row["baseline_so_units_per_day"]) is not int or row["baseline_so_units_per_day"] < 1:
            raise ValueError("Daily baseline SO must be a positive authored integer")
        if type(row["maximum_order_cases"]) is not int or row["maximum_order_cases"] < p["minimum_order_cases"]:
            raise ValueError("Capacity must accommodate the minimum order")
    names = [s["name"] for s in plan["scenarios"]]
    if not names or len(names) != len(set(names)):
        raise ValueError("Scenario names must be unique")
    for s in plan["scenarios"]:
        if Fraction(s["effect_multiplier"]) < 0 or type(s["delivery_delay_days"]) is not int or not 0 <= s["delivery_delay_days"] <= 14:
            raise ValueError("Invalid scenario assumptions")
    return plan


def simulate(promo, scenario, policy, effect, opening_stock, case_size, invoice_price):
    start = dt.date.fromisoformat(promo["start_date"]); end = dt.date.fromisoformat(promo["end_date"])
    final = end + policy["post_days"] * DAY
    base = Fraction(promo["baseline_so_units_per_day"])
    factor = Fraction(policy["incrementality_fraction"]) * Fraction(scenario["effect_multiplier"])
    demand = {}
    day = start
    while day <= final:
        rate = effect["gross_rate"] if day <= end else effect["post_rate"]
        # Negative deltas are avoided baseline consumption, bounded by the baseline.
        demand[day] = max(-base, base * rate * factor)
        day += DAY
    slack = max(Fraction(opening_stock) - base * policy["reserve_days"], Fraction())
    positive = sum((max(value,Fraction()) for value in demand.values()), Fraction())
    needed = max(positive - slack, Fraction())
    requested = max(math.ceil(needed / case_size), policy["minimum_order_cases"]) if needed else 0
    cases = min(requested, promo["maximum_order_cases"])
    delivered = cases * case_size
    receipt_day = start + scenario["delivery_delay_days"] * DAY
    final = max(final, receipt_day)
    balance = slack; fulfilled = avoided = unserved = Fraction()
    day = start
    while day <= final:
        if day == receipt_day:
            balance += delivered
        delta = demand.get(day, Fraction())
        if delta >= 0:
            sold = min(balance, delta); balance -= sold
            fulfilled += sold; unserved += delta-sold
        else:
            avoided -= delta; balance -= delta
        day += DAY
    if slack + delivered + avoided - fulfilled != balance:
        raise ValueError("Incremental stock ledger does not reconcile")
    amount = delivered * invoice_price
    return dict(scenario=scenario["name"],promo_id=promo["id"],customer_id=promo["customer_id"],product_id=promo["product_id"],
                order_date=str(start-policy["lead_days"]*DAY),expected_receipt_date=str(receipt_day),
                start_date=str(start),end_date=str(end),post_end_date=str(end+policy["post_days"]*DAY),
                opening_stock_units=opening_stock,baseline_reserved_units=base*policy["reserve_days"],
                opening_slack_units=slack,expected_positive_delta_so_units=positive,
                expected_net_delta_so_units=sum(demand.values(),Fraction()),
                post_q1_delta_so_units=sum((v for d,v in demand.items() if d.year==2027),Fraction()),
                fulfilled_positive_delta_so_units=fulfilled,unserved_positive_delta_so_units=unserved,
                avoided_baseline_so_units=avoided,requested_order_cases=requested,delivered_cases=cases,
                capacity_limited=cases<requested,additional_delivered_si_units=delivered,
                additional_si_satang=amount,additional_q4_si_satang=amount if receipt_day.year==2026 else 0,
                additional_q1_si_satang=amount if receipt_day.year==2027 else 0,
                closing_delta_stock_units=balance,invoice_price_satang=invoice_price,
                historical_promotions=effect["promotions"],historical_censored_promotions=effect["censored"],
                historical_gross_rate=effect["gross_rate"],historical_post_rate=effect["post_rate"],
                incrementality_fraction=Fraction(policy["incrementality_fraction"]),
                effect_multiplier=Fraction(scenario["effect_multiplier"]),discount_pct=promo["discount_pct"])


def build(root, plan):
    baseline = forecast(root)
    policy = plan["planning"]; as_of = dt.date.fromisoformat(policy["as_of"])
    products = {r["product_id"]:r for r in read(root,"dim_product")}
    stores = {r["store_id"]:r["customer_id"] for r in read(root,"dim_store")}
    customers = set(stores.values())
    inventory = defaultdict(int)
    for row in read(root,"fact_inventory_daily"):
        if row["date"] == str(as_of):
            inventory[stores[row["store_id"]],row["product_id"]] += int(row["closing_qty"])
    prices = {}
    for row in sorted(read(root,"dim_price"),key=lambda r:r["effective_from"]):
        if row["effective_from"] <= str(as_of):
            prices[row["product_id"]] = int(row["invoice_price_satang"])
    groups = defaultdict(list)
    for row in promotion_estimates(root,as_of):
        if row["method"]=="B1" and row["status"]=="available":
            groups[row["customer_id"],row["product_id"]].append(row)
    rows=[]
    for promo in plan["promotions"]:
        cid,pid=promo["customer_id"],promo["product_id"]
        if cid not in customers or pid not in products or pid not in prices:
            raise ValueError("Unknown planning retailer/product or missing as-of price")
        history=groups[cid,pid]
        if not history:
            raise ValueError("Historical observed promotion estimate is unavailable")
        effect=dict(gross_rate=sum(r["incremental_units"] for r in history)/sum(r["baseline_units"] for r in history),
                    post_rate=sum(r["post_incremental_units"] for r in history)/sum(r["post_baseline_units"] for r in history),
                    promotions=len(history),censored=sum(r["censored"] for r in history))
        for scenario in plan["scenarios"]:
            row=simulate(promo,scenario,policy,effect,inventory[cid,pid],int(products[pid]["case_size"]),prices[pid])
            row.update(category=products[pid]["category"],product_name=products[pid]["product_name"])
            rows.append(row)
    selected=[r for r in baseline["forecasts"] if r["method"]==baseline["selection"]["selected_method"]]
    monthly=[]; summaries=[]
    for scenario in plan["scenarios"]:
        scenario_rows=[r for r in rows if r["scenario"]==scenario["name"]]
        for b in selected:
            key=(b["customer_id"],b["category"],b["year"],b["month"])
            extra=sum(r["additional_si_satang"] for r in scenario_rows
                      if (r["customer_id"],r["category"],dt.date.fromisoformat(r["expected_receipt_date"]).year,dt.date.fromisoformat(r["expected_receipt_date"]).month)==key)
            monthly.append(dict(scenario=scenario["name"],customer_id=b["customer_id"],category=b["category"],
                                year=b["year"],month=b["month"],baseline_si_satang=b["forecast_satang"],
                                additional_si_satang=extra,scenario_si_satang=b["forecast_satang"]+extra))
        for b in baseline["outlook_summary"]:
            extra=sum(r["additional_q4_si_satang"] for r in scenario_rows if b["customer_id"]=="ALL" or r["customer_id"]==b["customer_id"])
            summaries.append(dict(scenario=scenario["name"],customer_id=b["customer_id"],
                                  baseline_full_year_satang=b["full_year_outlook_satang"],
                                  baseline_gap_satang=b["gap_to_annual_target_satang"],annual_target_satang=b["annual_target_satang"],
                                  additional_q4_si_satang=extra,scenario_full_year_satang=b["full_year_outlook_satang"]+extra,
                                  scenario_gap_satang=b["gap_to_annual_target_satang"]-extra))
    return dict(as_of=str(as_of),baseline_selection=baseline["selection"]["selected_method"],
                baseline_outlook=baseline["outlook_summary"],plan=plan,promotions=rows,monthly=monthly,outlook=summaries)
