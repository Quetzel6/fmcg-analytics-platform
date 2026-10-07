"""Isolated evaluation labels for the newly reserved receipt-risk scenario."""
import csv
import datetime as dt
from .risk_validation import binary_metrics

DAY = dt.timedelta(days=1)


def evaluate(root, rows, policy):
    with (root / "truth/truth_demand_daily.csv").open(newline="") as stream:
        lost = {(r["date"], r["store_id"], r["product_id"]): int(r["lost_qty"]) for r in csv.DictReader(stream)}
    observed = {(r["date"], r["store_id"], r["product_id"]) for r in rows}
    start = dt.date.fromisoformat(policy["evaluation_start"])
    end = dt.date.fromisoformat(policy["evaluation_end"])
    matched = []
    eligible = 0
    incomplete_future = 0
    for row in rows:
        day = dt.date.fromisoformat(row["date"])
        if not start <= day <= end:
            continue
        future = [(str(day + i * DAY), row["store_id"], row["product_id"]) for i in range(1, 8)]
        if not all(k in observed and k in lost for k in future):
            incomplete_future += 1
            continue
        if not row["history_complete"]:
            continue
        eligible += 1
        if row["receipt_score"] is None or row["risk_score"] is None:
            continue
        matched.append((row, any(lost[k] > 0 for k in future)))
    if not matched:
        raise ValueError("No complete matched evaluation observations")
    metrics = []
    for method, score, flag in (
            ("weekday_uncensored_cover", "risk_score", "risk_flag"),
            ("promised_receipt_path_v1", "receipt_score", "receipt_flag")):
        scored = [(row[score], row[flag], label) for row, label in matched]
        metrics.append(dict(method=method, cohort="reserved_2027_matched",
                            eligible_days=eligible, unscored_days=eligible-len(matched),
                            incomplete_future_days=incomplete_future, **binary_metrics(scored)))
    return metrics
