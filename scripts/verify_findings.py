"""
Reproduces every numeric claim stated in EDA_FINDINGS.md directly from the raw data sources,
and fails loudly (non-zero exit) if any recomputed value doesn't match what's stated.

How claims are written: every numeric claim in a findings document is followed by a tag
    0.1347<!--c:churn_rate-->
The tag names a claim whose value is recomputed here. The stated number is compared with
the recomputed one at the precision it was written with (0.1347 must match to 4 decimals).
A stated value starting with "<" (e.g. "<0.0001") passes if the recomputed value is below it.
A tag with an unknown name fails, so a claim can't be stated without a computation behind it.

The headline counts and the churn rate are recomputed with plain pandas (independent of eda/),
and the statistics come from the eda/ modules the notebook and runners use.

Run with `python -m scripts.verify_findings`.
"""

import re
import sqlite3
import sys
from contextlib import closing
from functools import lru_cache
from pathlib import Path

import pandas as pd

from eda.hypotheses import derive_pre_window_drivers, test_acquisition_channel, test_region, \
    test_pre_window_spend, test_pre_window_txn_count
from eda.leakage_checks import AS_OF, eligible_customers, trailing_window_diagnostics
from eda.load import load_customers, load_monthly_agg, load_transactions
from eda.profile import count_outliers, profile_distribution
from eda.time_checks import compare_row_level_vs_monthly_agg, monthly_volume_trend, trend_summary

DATA_ROOT = Path("data")
FINDINGS_FILES = [Path("EDA_FINDINGS.md"), Path("MODEL_RECOMMENDATION.md"), Path("DATA_ISSUES.md")]
CLAIM_PATTERN = re.compile(r"(<?[-+]?[\d.,]+(?:[eE][-+]?\d+)?)<!--c:([a-z0-9_]+)-->")


@lru_cache(maxsize=1)
def _sources():
    customers = load_customers(str(DATA_ROOT / "customers.csv"))
    transactions = load_transactions(str(DATA_ROOT / "transactions.db"))
    monthly = load_monthly_agg(str(DATA_ROOT / "transactions_monthly_agg.parquet"))
    return customers, transactions, monthly


def _raw_counts() -> dict:
    """Independent of eda/: straight pandas and sqlite on the raw files."""
    customers = pd.read_csv(DATA_ROOT / "customers.csv", parse_dates=["signup_date"])
    with closing(sqlite3.connect((DATA_ROOT / "transactions.db").resolve().as_uri() + "?mode=ro",
                                 uri=True)) as conn:
        txns = pd.read_sql("SELECT customer_id, txn_timestamp FROM transactions", conn,
                           parse_dates=["txn_timestamp"])
    last = txns.groupby("customer_id")["txn_timestamp"].max()
    days_since_last = (AS_OF - customers["customer_id"].map(last)).dt.days
    # Label rule: churned iff whole days since last purchase exceed 90; no purchase = churned.
    label_rule = (days_since_last.isna() | (days_since_last > 90)).astype(int)
    return {"customers": customers, "txns": txns, "label_rule": label_rule}


def _eligible_churn_rate() -> float:
    customers, _, _ = _sources()
    eligible = eligible_customers(customers, AS_OF)
    return float(eligible["churned"].mean())


def _signup_in_window() -> tuple[int, float]:
    customers, _, _ = _sources()
    late = customers[customers["signup_date"] >= AS_OF - pd.Timedelta(days=90)]
    return int(len(late)), float(late["churned"].mean())


def _dist(column_name: str) -> dict:
    _, transactions, _ = _sources()
    return profile_distribution(transactions[column_name])


def _hypothesis(test_fn) -> dict:
    customers, transactions, _ = _sources()
    return test_fn(derive_pre_window_drivers(customers, transactions, AS_OF))


def _trend() -> dict:
    _, transactions, _ = _sources()
    return trend_summary(monthly_volume_trend(transactions), "txn_count")


def _comparison_row(month: str) -> pd.Series:
    _, transactions, monthly = _sources()
    comp = compare_row_level_vs_monthly_agg(transactions, monthly)
    return comp.loc[comp["month"] == pd.Timestamp(month)].iloc[0]


def _months_with_disagreement() -> int:
    _, transactions, monthly = _sources()
    comp = compare_row_level_vs_monthly_agg(transactions, monthly)
    bad = (comp["txn_count_diff"] != 0) | (comp["customer_months_db_only"] > 0) \
        | (comp["customer_months_pq_only"] > 0) | (comp["customer_months_txn_count_mismatch"] > 0) \
        | (comp["customer_months_total_amount_mismatch"] > 0)
    return int(bad.sum())


def _label_rule_match() -> int:
    raw = _raw_counts()
    return int(((raw["label_rule"]) == raw["customers"]["churned"]).sum())


def _window_24h_match() -> int:
    """Customers the plain 90x24h window reproduces: no purchase in [as_of - 90 days, as_of)."""
    raw = _raw_counts()
    start = AS_OF - pd.Timedelta(days=90)
    in_window = set(raw["txns"].loc[(raw["txns"]["txn_timestamp"] >= start)
                                    & (raw["txns"]["txn_timestamp"] < AS_OF), "customer_id"])
    window_rule = (~raw["customers"]["customer_id"].isin(in_window)).astype(int)
    return int((window_rule == raw["customers"]["churned"]).sum())


def _diag(key: str) -> float:
    customers, transactions, _ = _sources()
    return float(trailing_window_diagnostics(customers, transactions, AS_OF)[key])


def compute_claims() -> dict:
    """Every claim ID that a findings document may cite, recomputed from the raw data."""
    raw = _raw_counts()
    customers = raw["customers"]
    txns = raw["txns"]
    n_signup_window, signup_window_churn = _signup_in_window()
    amount = _dist("amount")
    outliers = count_outliers(_sources()[1]["amount"])
    rb = _hypothesis(test_pre_window_spend)
    july = _comparison_row("2026-07-01")
    trend = _trend()
    return {
        "n_customers": len(customers),
        "churned_count": int(customers["churned"].sum()),
        "churn_rate": float(customers["churned"].mean()),
        "zero_activity_count": int((~customers["customer_id"].isin(txns["customer_id"])).sum()),
        "zero_activity_churned_count": int(
            customers.loc[~customers["customer_id"].isin(txns["customer_id"]), "churned"].sum()),
        "txn_rows": len(txns),
        "monthly_rows": len(_sources()[2]),
        "n_months": int(trend["n_months"]),
        "channel_cramers_v": _hypothesis(test_acquisition_channel)["effect_size_or_magnitude"],
        "region_cramers_v": _hypothesis(test_region)["effect_size_or_magnitude"],
        "label_rule_match_count": _label_rule_match(),
        "window_24h_match_count": _window_24h_match(),
        "baseline_accuracy": 1 - float(customers["churned"].mean()),
        "eligible_n": len(eligible_customers(customers, AS_OF)),
        "eligible_churned_count": int(eligible_customers(customers, AS_OF)["churned"].sum()),
        "eligible_churn_rate": _eligible_churn_rate(),
        "eligible_baseline_accuracy": 1 - _eligible_churn_rate(),
        "signup_in_window_n": n_signup_window,
        "signup_in_window_churn_rate": signup_window_churn,
        "amount_mean": amount["mean"],
        "amount_median": amount["median"],
        "amount_skew": amount["skew"],
        "amount_outlier_count": outliers["n_outliers"],
        "amount_upper_fence": outliers["bound_high"],
        "channel_chi2_p": _hypothesis(test_acquisition_channel)["p_value"],
        "region_chi2_p": _hypothesis(test_region)["p_value"],
        "pre_txn_count_mwu_p": _hypothesis(test_pre_window_txn_count)["p_value"],
        "pre_spend_mwu_p": rb["p_value"],
        "pre_spend_rank_biserial": rb["effect_size_or_magnitude"],
        "dsl_mwu_p_below": _diag("days_since_last_txn_mwu_p"),
        "churned_min_days_since_last": _diag("days_since_last_txn_min_churned"),
        "churned_max_trailing_90d_spend": _diag("trailing_90d_spend_max_churned"),
        "trend_slope_per_month": trend["slope_per_month"],
        "trend_spearman_rho": trend["spearman_rho"],
        "months_with_source_disagreement": _months_with_disagreement(),
        "july_2026_db_txn_count": int(july["db_txn_count"]),
        "july_2026_pq_txn_count": int(july["pq_txn_count"]),
        "july_2026_txn_gap": int(july["txn_count_diff"]),
        "july_2026_db_only_customer_months": int(july["customer_months_db_only"]),
        "july_2026_count_mismatch_customer_months": int(july["customer_months_txn_count_mismatch"]),
        "july_2026_amount_gap": float(july["total_amount_diff"]),
    }


def _matches(stated: str, recomputed) -> bool:
    if stated.startswith("<"):
        return float(recomputed) < float(stated[1:].replace(",", ""))
    value = float(stated.replace(",", ""))
    decimals = len(stated.split(".")[1]) if "." in stated else 0
    tolerance = 0.5 * 10 ** (-decimals) + 1e-9
    return abs(value - float(recomputed)) <= tolerance


def check_findings(findings_paths: list[Path] = FINDINGS_FILES) -> list[str]:
    """Return failure messages across the findings documents; an empty list means all pass."""
    claims = compute_claims()
    failures = []
    for path in findings_paths:
        found = CLAIM_PATTERN.findall(Path(path).read_text(encoding="utf-8"))
        if not found:
            failures.append(f"{path}: no <!--c:...--> claims found")
        for stated, claim_id in found:
            if claim_id not in claims:
                failures.append(f"{path} {claim_id}: stated {stated}, but no computation exists")
            elif not _matches(stated, claims[claim_id]):
                failures.append(f"{path} {claim_id}: stated {stated}, recomputed {claims[claim_id]}")
    return failures


def main() -> int:
    failures = check_findings()
    total = sum(len(CLAIM_PATTERN.findall(Path(p).read_text(encoding="utf-8"))) for p in FINDINGS_FILES)
    print(f"checked {total} stated claims in {', '.join(str(p) for p in FINDINGS_FILES)}")
    if failures:
        for message in failures:
            print("FAIL", message)
        return 1
    print("PASS: every stated claim reproduces from the raw data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
