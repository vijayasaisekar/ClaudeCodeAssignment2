"""
Tests for eda/time_checks.py and eda/leakage_checks.py against constructed input.
"""

import pandas as pd

from eda.leakage_checks import check_no_post_as_of_rows_used, flag_label_circular_drivers
from eda.time_checks import compare_row_level_vs_monthly_agg, monthly_volume_trend, trend_summary


def _txns(rows):
    """rows: list of (customer_id, 'YYYY-MM-DD', amount)."""
    df = pd.DataFrame(rows, columns=["customer_id", "txn_timestamp", "amount"])
    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    df["is_returned"] = 0
    return df


def _agg_from(transactions):
    """A monthly extract that agrees with the row-level table by construction."""
    month = transactions["txn_timestamp"].dt.to_period("M").dt.to_timestamp()
    return (transactions.assign(txn_month=month)
            .groupby(["customer_id", "txn_month"])
            .agg(txn_count=("amount", "size"), total_amount=("amount", "sum"),
                 return_count=("is_returned", "sum"))
            .reset_index())


def test_monthly_volume_trend_detects_growth():
    rows = []
    for month_index, n in enumerate([2, 4, 6, 8, 10, 12]):
        for k in range(n):
            rows.append((k, f"2025-{month_index + 1:02d}-10", 10.0))
    trend = monthly_volume_trend(_txns(rows))
    assert trend["txn_count"].tolist() == [2, 4, 6, 8, 10, 12]
    summary = trend_summary(trend, "txn_count")
    assert summary["direction"] == "increasing"
    assert summary["spearman_rho"] == 1.0
    assert summary["slope_per_month"] > 0


def test_compare_row_level_vs_monthly_agg_detects_known_mismatch():
    transactions = _txns([(1, "2026-06-01", 10.0), (1, "2026-07-02", 20.0),
                          (2, "2026-07-05", 30.0)])
    monthly = _agg_from(transactions)
    # Customer 2 has 1 July transaction row-level; the extract wrongly records 3.
    monthly.loc[(monthly["customer_id"] == 2) & (monthly["txn_month"] == pd.Timestamp("2026-07-01")),
                "txn_count"] = 3
    comparison = compare_row_level_vs_monthly_agg(transactions, monthly)
    july = comparison.loc[comparison["month"] == pd.Timestamp("2026-07-01")].iloc[0]
    june = comparison.loc[comparison["month"] == pd.Timestamp("2026-06-01")].iloc[0]
    assert july["txn_count_diff"] == -2
    assert july["customer_months_txn_count_mismatch"] == 1
    assert june["txn_count_diff"] == 0


def test_compare_row_level_vs_monthly_agg_confirms_agreement_when_consistent():
    transactions = _txns([(1, "2026-06-01", 10.0), (1, "2026-07-02", 20.0),
                          (2, "2026-07-05", 30.0)])
    comparison = compare_row_level_vs_monthly_agg(transactions, _agg_from(transactions))
    assert (comparison["txn_count_diff"] == 0).all()
    assert (comparison["total_amount_diff"].abs() < 0.01).all()
    assert (comparison["customer_months_db_only"] == 0).all()
    assert (comparison["customer_months_pq_only"] == 0).all()


def test_flag_label_circular_drivers_flags_trailing_window_features():
    result = flag_label_circular_drivers(["days_since_last_txn", "trailing_90d_spend"])
    assert set(result["flagged"]) == {"days_since_last_txn", "trailing_90d_spend"}
    assert "90-day" in result["flagged"]["trailing_90d_spend"]
    assert result["not_flagged"] == []


def test_flag_label_circular_drivers_does_not_flag_legitimate_driver():
    result = flag_label_circular_drivers(["tenure_days", "pre_window_spend"])
    assert result["flagged"] == {}
    assert set(result["not_flagged"]) == {"tenure_days", "pre_window_spend"}


def test_post_as_of_check_flags_rows_after_cutoff():
    transactions = _txns([(1, "2026-07-31", 10.0), (2, "2026-08-02", 5.0)])
    result = check_no_post_as_of_rows_used(transactions, "2026-08-01")
    assert result["passed"] is False
    assert result["n_post_as_of_rows_in_source"] == 1
    clean = check_no_post_as_of_rows_used(transactions.iloc[:1], "2026-08-01")
    assert clean["passed"] is True
