"""
Profiling tests against small constructed DataFrames with a known shape.
"""

import pandas as pd

from eda.profile import (
    count_outliers,
    count_zero_activity_customers,
    profile_distribution,
    profile_missingness,
    profile_schema,
)


def test_profile_schema_reports_expected_columns_and_dtypes():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    schema = profile_schema(df)
    assert schema["columns"] == ["a", "b"]
    assert schema["dtypes"]["a"].startswith("int")
    assert schema["n_rows"] == 2


def test_profile_missingness_does_not_conflate_zero_activity_with_missing():
    customers = pd.DataFrame({"customer_id": [1, 2, 3], "churned": [0, 1, 1]})
    transactions = pd.DataFrame({"customer_id": [1, 1], "amount": [5.0, None]})
    assert count_zero_activity_customers(customers, transactions) == 2
    # The one real null is counted by missingness; zero-activity customers are not nulls.
    assert profile_missingness(transactions) == {"customer_id": 0, "amount": 1}


def test_profile_distribution_detects_right_skew():
    series = pd.Series([1.0] * 20 + [100.0])
    dist = profile_distribution(series)
    assert dist["skew_direction"] == "right"
    assert dist["mean"] > dist["median"]


def test_count_outliers_flags_known_outlier():
    series = pd.Series([10.0, 11.0, 12.0, 10.5, 11.5, 500.0])
    result = count_outliers(series)
    assert result["n_outliers"] == 1
    assert result["bound_low"] < 10.0 < 11.5 < result["bound_high"] < 500.0

def test_profile_rejects_empty_input_explicitly():
    """Zero rows must raise, not return a silent empty or NaN summary."""
    import pytest

    from eda.profile import count_zero_activity_customers as czc

    with pytest.raises(ValueError):
        profile_distribution(pd.Series([], dtype=float))
    with pytest.raises(ValueError):
        count_outliers(pd.Series([], dtype=float))
    with pytest.raises(ValueError):
        czc(pd.DataFrame({"customer_id": []}), pd.DataFrame({"customer_id": [1]}))
