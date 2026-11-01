"""
Runs eda/profile.py across all three sources and prints a human-readable summary.

Run with `python -m scripts.run_profile` (not `python scripts/run_profile.py`) so `eda`
resolves as an import.
"""

import json
from pathlib import Path

from eda.load import load_customers, load_monthly_agg, load_transactions
from eda.profile import (
    count_outliers,
    count_zero_activity_customers,
    profile_distribution,
    profile_missingness,
    profile_schema,
)

ARTIFACTS = Path("outputs/artifacts")


def build_profile() -> dict:
    customers = load_customers()
    transactions = load_transactions()
    monthly = load_monthly_agg()
    return {
        "schema": {
            "customers": profile_schema(customers),
            "transactions": profile_schema(transactions),
            "monthly_agg": profile_schema(monthly),
        },
        "missingness": {
            "customers": profile_missingness(customers),
            "transactions": profile_missingness(transactions),
            "monthly_agg": profile_missingness(monthly),
        },
        "zero_activity_customers": count_zero_activity_customers(customers, transactions),
        "amount_distribution": profile_distribution(transactions["amount"]),
        "amount_outliers": count_outliers(transactions["amount"]),
        "churn_rate": float(customers["churned"].mean()),
        "churned_count": int(customers["churned"].sum()),
        "n_customers": int(len(customers)),
    }


def main() -> None:
    profile = build_profile()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "profile_summary.json").write_text(json.dumps(profile, indent=2, default=str))

    print(f"customers: {profile['n_customers']} rows, churned {profile['churned_count']}, "
          f"churn rate {profile['churn_rate']:.4f}")
    print(f"zero-activity customers (no rows in transactions.db): {profile['zero_activity_customers']}")
    print("missingness (customers):", profile["missingness"]["customers"])
    print("missingness (transactions):", profile["missingness"]["transactions"])
    print("missingness (monthly_agg):", profile["missingness"]["monthly_agg"])
    dist = profile["amount_distribution"]
    print(f"amount: mean {dist['mean']:.2f}, median {dist['median']:.2f}, skew {dist['skew']:.2f} "
          f"({dist['skew_direction']}), min {dist['min']:.2f}, max {dist['max']:.2f}")
    out = profile["amount_outliers"]
    print(f"amount outliers ({out['rule']}): {out['n_outliers']} rows outside "
          f"[{out['bound_low']:.2f}, {out['bound_high']:.2f}]")


if __name__ == "__main__":
    main()
