"""
Pure I/O loaders for the three heterogeneous raw sources described in the companion
feature-pipeline assignment's data_dictionary.md (or, if you don't have that document, from
your own Stage 0 read of the raw sources). No analysis logic belongs here — only loading and
basic type coercion, so loading can be unit-tested and reused independently of
`profile.py`, `hypotheses.py`, `time_checks.py`, and `leakage_checks.py`.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd


def load_customers(path: str = "data/customers.csv") -> pd.DataFrame:
    """Load customers.csv: one row per customer, with the churn label, unmodified otherwise."""
    customers = pd.read_csv(path)
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    return customers


def load_transactions(path: str = "data/transactions.db") -> pd.DataFrame:
    """Load the row-level `transactions` table from the SQLite database (opened read-only)."""
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        transactions = pd.read_sql("SELECT * FROM transactions", conn)
    transactions["txn_timestamp"] = pd.to_datetime(transactions["txn_timestamp"])
    transactions["is_returned"] = transactions["is_returned"].astype(int)
    return transactions


def load_monthly_agg(path: str = "data/transactions_monthly_agg.parquet") -> pd.DataFrame:
    """Load the pre-aggregated customer x month parquet extract, as-is except for dtypes.

    Customer-months with no activity have no row in this extract.
    """
    monthly = pd.read_parquet(path)
    monthly["txn_month"] = pd.to_datetime(monthly["txn_month"])
    return monthly
