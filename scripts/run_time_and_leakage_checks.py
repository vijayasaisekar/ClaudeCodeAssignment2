"""
Runs eda/time_checks.py and eda/leakage_checks.py and prints/saves the results.

Run with `python -m scripts.run_time_and_leakage_checks`.
"""

import json
from pathlib import Path

from eda.leakage_checks import (
    AS_OF,
    check_no_post_as_of_rows_used,
    flag_label_circular_drivers,
    trailing_window_diagnostics,
)
from eda.load import load_customers, load_monthly_agg, load_transactions
from eda.time_checks import compare_row_level_vs_monthly_agg, monthly_volume_trend, trend_summary

ARTIFACTS = Path("outputs/artifacts")
CANDIDATE_DRIVERS = ["acquisition_channel", "region", "tenure_days", "pre_window_txn_count",
                     "pre_window_spend", "days_since_last_txn", "trailing_90d_spend"]


def build_checks() -> dict:
    customers = load_customers()
    transactions = load_transactions()
    monthly_agg = load_monthly_agg()

    trend = monthly_volume_trend(transactions)
    comparison = compare_row_level_vs_monthly_agg(transactions, monthly_agg)
    return {
        "trend_summary": trend_summary(trend, "txn_count"),
        "trend_monthly": trend.assign(month=trend["month"].dt.strftime("%Y-%m")).to_dict("records"),
        "multi_source_comparison": comparison.assign(
            month=comparison["month"].dt.strftime("%Y-%m")).to_dict("records"),
        "leakage_flags": flag_label_circular_drivers(CANDIDATE_DRIVERS),
        "post_as_of_check": check_no_post_as_of_rows_used(transactions, str(AS_OF.date())),
        "trailing_window_diagnostics": trailing_window_diagnostics(customers, transactions),
    }


def main() -> None:
    checks = build_checks()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "time_leakage_checks.json").write_text(json.dumps(checks, indent=2, default=str))

    t = checks["trend_summary"]
    print(f"monthly txn_count trend: {t['direction']}, slope {t['slope_per_month']:.1f} rows/month, "
          f"Spearman rho {t['spearman_rho']:.3f} over {t['n_months']} months "
          f"({t['first_month']} to {t['last_month']})")
    diffs = [r for r in checks["multi_source_comparison"]
             if r["txn_count_diff"] != 0 or r["customer_months_db_only"] or r["customer_months_pq_only"]
             or r["customer_months_txn_count_mismatch"] or r["customer_months_total_amount_mismatch"]]
    print(f"multi-source months with any disagreement: {len(diffs)}")
    for r in diffs:
        print(f"  {r['month']}: row-level {r['db_txn_count']} txns vs extract {r['pq_txn_count']} "
              f"(diff {r['txn_count_diff']}); customer-months db-only {r['customer_months_db_only']}, "
              f"amount diff {r['total_amount_diff']}")
    flags = checks["leakage_flags"]
    print("leakage-flagged drivers:", list(flags["flagged"]))
    print("not flagged:", flags["not_flagged"], "unclassified:", flags["unclassified"])
    print("post-as-of check:", checks["post_as_of_check"]["note"], "passed =",
          checks["post_as_of_check"]["passed"])
    d = checks["trailing_window_diagnostics"]
    print(f"trailing-window diagnostics: churned customers' min days-since-last-txn = "
          f"{d['days_since_last_txn_min_churned']:.0f}; max trailing-90d spend among churned = "
          f"{d['trailing_90d_spend_max_churned']:.2f}")


if __name__ == "__main__":
    main()
