"""
Loader tests against the real provided files: expected columns, dtypes, and sane row counts.
"""

from eda.load import load_customers, load_monthly_agg, load_transactions


def test_load_customers_schema_and_row_count():
    customers = load_customers()
    assert list(customers.columns) == ["customer_id", "signup_date", "acquisition_channel",
                                       "region", "churned"]
    assert customers["signup_date"].dtype.kind == "M"
    assert 1000 <= len(customers) <= 2000
    assert customers["customer_id"].is_unique


def test_load_transactions_schema_and_row_count():
    transactions = load_transactions()
    assert list(transactions.columns) == ["customer_id", "txn_timestamp", "category", "channel",
                                          "amount", "is_returned"]
    assert transactions["txn_timestamp"].dtype.kind == "M"
    assert set(transactions["is_returned"].unique()) <= {0, 1}
    assert 10_000 <= len(transactions) <= 20_000


def test_load_monthly_agg_schema_and_row_count():
    monthly = load_monthly_agg()
    assert list(monthly.columns) == ["customer_id", "txn_month", "txn_count", "total_amount",
                                     "return_count"]
    assert monthly["txn_month"].dtype.kind == "M"
    assert monthly["txn_month"].dt.day.eq(1).all()
    assert not monthly.duplicated(["customer_id", "txn_month"]).any()
