"""
One pure function per candidate churn-driver named in your confirmed `eda_review.md`.

Each function should:
- Take already-loaded/derived data in (no I/O here) and return a structured result out:
  {"driver": str, "test": str, "statistic": float, "p_value": float,
   "effect_size_or_magnitude": ..., "higher_group": "churned"/"not_churned"/None}.
- Choose the test that matches the variable's actual shape per eda_review.md (chi-square for
  a categorical driver, Mann-Whitney U for a skewed/non-normal continuous driver, a t-test
  only after checking the normality assumption actually holds) — do not default to a t-test
  for everything.
- Report the result honestly even when it is not statistically significant. A null result is
  a real finding, not a failure to report.

All drivers are tested on the eligible population (customers who signed up before the label
window opened), with the transaction-based drivers computed strictly before the window.
"""

import numpy as np
import pandas as pd
from scipy import stats

from eda.leakage_checks import AS_OF, eligible_customers, label_window


def derive_pre_window_drivers(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: pd.Timestamp = AS_OF,
) -> pd.DataFrame:
    """Eligible customers with pre-window behaviour drivers attached.

    pre_window_txn_count and pre_window_spend use only transactions before the label window
    opens, so they cannot contain the label's own period. Customers with no pre-window rows
    get 0 (a real zero, not a missing value).
    """
    start, _ = label_window(as_of)
    pre = transactions[transactions["txn_timestamp"] < start]
    grouped = pre.groupby("customer_id")["amount"].agg(["size", "sum"])
    frame = eligible_customers(customers, as_of).set_index("customer_id")
    frame["pre_window_txn_count"] = grouped["size"].reindex(frame.index).fillna(0).astype(int)
    frame["pre_window_spend"] = grouped["sum"].reindex(frame.index).fillna(0.0)
    return frame.reset_index()


def _chi_square_result(frame: pd.DataFrame, driver: str) -> dict:
    """Chi-square test of independence between a categorical driver and the churn label."""
    if frame[driver].nunique() < 2:
        raise ValueError(f"{driver}: needs at least two levels to test against churn")
    table = pd.crosstab(frame[driver], frame["churned"])
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    n = table.to_numpy().sum()
    k = min(table.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * k)))
    churn_rate = frame.groupby(driver)["churned"].mean()
    return {
        "driver": driver,
        "test": "chi-square test of independence",
        "statistic": float(chi2),
        "p_value": float(p),
        "effect_size_or_magnitude": cramers_v,
        "effect_metric": "Cramer's V",
        "higher_group": None,
        "highest_churn_group": str(churn_rate.idxmax()),
        "highest_churn_rate": float(churn_rate.max()),
        "lowest_churn_rate": float(churn_rate.min()),
        "n": int(n),
    }


def _mann_whitney_result(frame: pd.DataFrame, driver: str) -> dict:
    """Two-sided Mann-Whitney U of a skewed numeric driver, churned vs not churned."""
    churned = frame.loc[frame["churned"] == 1, driver]
    kept = frame.loc[frame["churned"] == 0, driver]
    if churned.empty or kept.empty:
        raise ValueError(f"{driver}: both churned and not-churned groups must be non-empty")
    mwu = stats.mannwhitneyu(churned, kept, alternative="two-sided")
    n1, n2 = len(churned), len(kept)
    rank_biserial = 2 * mwu.statistic / (n1 * n2) - 1
    higher = "churned" if churned.median() > kept.median() else (
        "not_churned" if kept.median() > churned.median() else None)
    return {
        "driver": driver,
        "test": "Mann-Whitney U (two-sided)",
        "statistic": float(mwu.statistic),
        "p_value": float(mwu.pvalue),
        "effect_size_or_magnitude": float(rank_biserial),
        "effect_metric": "rank-biserial r (positive = churned tends higher)",
        "higher_group": higher,
        "highest_churn_group": None,
        "highest_churn_rate": None,
        "lowest_churn_rate": None,
        "n": int(n1 + n2),
        "skew": float(frame[driver].skew()),
    }


def test_acquisition_channel(frame: pd.DataFrame) -> dict:
    """acquisition_channel (categorical, 4 levels): chi-square vs churned."""
    return _chi_square_result(frame, "acquisition_channel")


def test_region(frame: pd.DataFrame) -> dict:
    """region (categorical, 4 levels): chi-square vs churned. Expected null."""
    return _chi_square_result(frame, "region")


def test_pre_window_txn_count(frame: pd.DataFrame) -> dict:
    """pre_window_txn_count (right-skewed count, heavy zeros): Mann-Whitney U."""
    return _mann_whitney_result(frame, "pre_window_txn_count")


def test_pre_window_spend(frame: pd.DataFrame) -> dict:
    """pre_window_spend (right-skewed money, heavy zeros): Mann-Whitney U."""
    return _mann_whitney_result(frame, "pre_window_spend")


HYPOTHESES = [test_acquisition_channel, test_region, test_pre_window_txn_count,
              test_pre_window_spend]


def run_all_hypotheses(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: pd.Timestamp = AS_OF,
) -> list[dict]:
    """Run every candidate-driver test on the eligible population."""
    frame = derive_pre_window_drivers(customers, transactions, as_of)
    return [test(frame) for test in HYPOTHESES]
