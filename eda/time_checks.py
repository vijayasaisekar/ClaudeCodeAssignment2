"""
Time-dimension diagnostics: the monthly transaction-volume trend (non-stationarity check),
and the multi-source agreement check between the row-level table and the pre-aggregated
monthly parquet extract.
"""

import numpy as np
import pandas as pd
from scipy import stats


def _to_month_start(timestamps: pd.Series) -> pd.Series:
    """Return the first-of-month timestamp, as a datetime64[ns] column."""
    return pd.to_datetime(timestamps).dt.to_period("M").dt.to_timestamp().astype("datetime64[ns]")


def monthly_volume_trend(transactions: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar month: txn_count, total_amount and n_customers, chronological."""
    month = _to_month_start(transactions["txn_timestamp"])
    grouped = transactions.groupby(month).agg(
        txn_count=("amount", "size"),
        total_amount=("amount", "sum"),
        n_customers=("customer_id", "nunique"),
    )
    grouped.index.name = "month"
    return grouped.reset_index().sort_values("month").reset_index(drop=True)


def trend_summary(monthly: pd.DataFrame, column: str = "txn_count") -> dict:
    """Direction and magnitude of a monthly series: OLS slope per month and Spearman rho."""
    x = np.arange(len(monthly))
    y = monthly[column].to_numpy(dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    rho, p = stats.spearmanr(x, y)
    return {
        "column": column,
        "n_months": int(len(monthly)),
        "first_month": str(monthly["month"].iloc[0].date()),
        "last_month": str(monthly["month"].iloc[-1].date()),
        "slope_per_month": slope,
        "spearman_rho": float(rho),
        "spearman_p": float(p),
        "direction": "increasing" if rho > 0 else "decreasing",
    }


def compare_row_level_vs_monthly_agg(
    transactions: pd.DataFrame,
    monthly_agg: pd.DataFrame,
) -> pd.DataFrame:
    """Reaggregate `transactions` to (customer_id, month) and compare with `monthly_agg`.

    Returns one row per calendar month with: the row-level and extract txn_count and
    total_amount totals, the differences (row-level minus extract), the number of
    customer-months only in one source, and the number of customer-months present in both
    whose txn_count or total_amount disagree. Nothing is assumed to agree.
    """
    rows = transactions.assign(txn_month=_to_month_start(transactions["txn_timestamp"]))
    db = rows.groupby(["customer_id", "txn_month"]).agg(
        db_txn_count=("amount", "size"),
        db_total_amount=("amount", "sum"),
    ).reset_index()

    pq = monthly_agg.assign(txn_month=pd.to_datetime(monthly_agg["txn_month"]).astype("datetime64[ns]"))
    pq = pq.rename(columns={"txn_count": "pq_txn_count", "total_amount": "pq_total_amount"})
    pq = pq[["customer_id", "txn_month", "pq_txn_count", "pq_total_amount"]]

    merged = db.merge(pq, on=["customer_id", "txn_month"], how="outer", indicator=True)
    merged["txn_count_mismatch"] = (
        (merged["_merge"] == "both")
        & (merged["db_txn_count"] != merged["pq_txn_count"])
    )
    merged["total_amount_mismatch"] = (
        (merged["_merge"] == "both")
        & ((merged["db_total_amount"] - merged["pq_total_amount"]).abs() > 0.005)
    )
    merged["db_only"] = merged["_merge"] == "left_only"
    merged["pq_only"] = merged["_merge"] == "right_only"

    per_month = merged.groupby("txn_month").agg(
        db_txn_count=("db_txn_count", "sum"),
        pq_txn_count=("pq_txn_count", "sum"),
        db_total_amount=("db_total_amount", "sum"),
        pq_total_amount=("pq_total_amount", "sum"),
        customer_months_db_only=("db_only", "sum"),
        customer_months_pq_only=("pq_only", "sum"),
        customer_months_txn_count_mismatch=("txn_count_mismatch", "sum"),
        customer_months_total_amount_mismatch=("total_amount_mismatch", "sum"),
    ).reset_index().rename(columns={"txn_month": "month"})
    per_month["txn_count_diff"] = per_month["db_txn_count"] - per_month["pq_txn_count"]
    per_month["total_amount_diff"] = (per_month["db_total_amount"]
                                      - per_month["pq_total_amount"]).round(2)
    return per_month.sort_values("month").reset_index(drop=True)
