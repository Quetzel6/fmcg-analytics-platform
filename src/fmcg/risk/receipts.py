"""Past-only order snapshots and a fixed promised-receipt stock path."""
import datetime as dt
from collections import defaultdict
from fractions import Fraction
import tomllib

from ..analytics.metrics import read
from .metrics import build as build_cover

DAY = dt.timedelta(days=1)


def load_policy(path):
    with path.open("rb") as stream:
        policy = tomllib.load(stream)["receipt_risk"]
    if (policy["lookback_days"], policy["horizon_days"], policy["method"]) != (28, 7, "promised_receipt_path_v1"):
        raise ValueError("Receipt protocol requires fixed 28/7-day windows and v1 method")
    if (type(policy["receipt_numerator"]) is not int or type(policy["receipt_denominator"]) is not int
            or not 0 < policy["receipt_numerator"] <= policy["receipt_denominator"]):
        raise ValueError("Receipt fraction must be in (0, 1]")
    if (policy["receipt_numerator"], policy["receipt_denominator"]) != (4, 5):
        raise ValueError("Receipt v1 is fixed at 4/5; new policies need a separate evaluation protocol")
    start = dt.date.fromisoformat(policy["evaluation_start"])
    end = dt.date.fromisoformat(policy["evaluation_end"])
    if start != dt.date(2027, 1, 1) or end != dt.date(2027, 9, 23):
        raise ValueError("The reserved evaluation period is 2027-01-01 through 2027-09-23")
    return policy


def parse_order(row):
    return dict(order_date=dt.date.fromisoformat(row["order_date"]),
                promised_date=dt.date.fromisoformat(row["promised_date"]),
                delivered_date=dt.date.fromisoformat(row["delivered_date"]) if row["delivered_date"] else None,
                ordered_qty=int(row["ordered_qty"]))


def snapshot(orders, day):
    # Actual receipt evidence closes a line only after it has been observed.
    # Future delivery dates are used only for this as-of status, never as arrival predictions.
    return [r for r in orders if r["order_date"] <= day
            and (r["delivered_date"] is None or r["delivered_date"] > day)]


def project(day, closing, mean, orders, policy):
    opened = snapshot(orders, day)
    overdue = sum(r["ordered_qty"] for r in opened if r["promised_date"] <= day)
    fraction = Fraction(policy["receipt_numerator"], policy["receipt_denominator"])
    arrivals = defaultdict(Fraction)
    for row in opened:
        offset = (row["promised_date"] - day).days
        if 1 <= offset <= 7:
            arrivals[offset] += row["ordered_qty"] * fraction
    base = dict(known_open_lines=len(opened), overdue_ordered_qty=overdue,
                credited_receipt_qty=sum(arrivals.values(), Fraction()),
                receipt_score=None, receipt_flag=None, minimum_projected_qty=None)
    if mean is None or mean <= 0:
        return base
    balance = Fraction(closing)
    path = []
    for offset in range(1, 8):
        balance += arrivals[offset] - mean
        path.append(balance)
    minimum = min(path)
    # With no receipts, this equals the existing seven-day cover score exactly.
    score = 7 * mean / (14 * mean + minimum)
    base.update(receipt_score=score, receipt_flag=minimum < 0, minimum_projected_qty=minimum)
    return base


def build(root, as_of, policy):
    orders = defaultdict(list)
    for row in read(root, "fact_order_line"):
        orders[row["store_id"], row["product_id"]].append(parse_order(row))
    for values in orders.values():
        values.sort(key=lambda r: r["order_date"])
    output = []
    active = []
    pointer = 0
    previous = None
    for row in build_cover(root, as_of):
        key = (row["store_id"], row["product_id"])
        if key != previous:
            active = []; pointer = 0; previous = key
        day = dt.date.fromisoformat(row["date"])
        lines = orders[key]
        while pointer < len(lines) and lines[pointer]["order_date"] <= day:
            active.append(lines[pointer]); pointer += 1
        active = snapshot(active, day)
        row.update(project(day, row["closing_qty"], row["uncensored_mean_daily"], active, policy))
        output.append(row)
    return output
