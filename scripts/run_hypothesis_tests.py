"""
Runs every hypothesis test function in eda/hypotheses.py for the candidate drivers named in
eda_review.md, and prints/saves a results table.

Run with `python -m scripts.run_hypothesis_tests`.
"""

from pathlib import Path

import pandas as pd

from eda.hypotheses import run_all_hypotheses
from eda.load import load_customers, load_transactions

ARTIFACTS = Path("outputs/artifacts")
COLUMNS = ["driver", "test", "n", "statistic", "p_value", "effect_size_or_magnitude",
           "effect_metric", "higher_group", "highest_churn_group", "highest_churn_rate"]


def build_results_table() -> pd.DataFrame:
    customers = load_customers()
    transactions = load_transactions()
    return pd.DataFrame(run_all_hypotheses(customers, transactions))[COLUMNS]


def main() -> None:
    table = build_results_table()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(ARTIFACTS / "hypothesis_results.csv", index=False)
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(table.to_string(index=False))
    print("\nSignificant at alpha=0.05:", table.loc[table["p_value"] < 0.05, "driver"].tolist())
    print("Not significant at alpha=0.05 (null results):",
          table.loc[table["p_value"] >= 0.05, "driver"].tolist())


if __name__ == "__main__":
    main()
