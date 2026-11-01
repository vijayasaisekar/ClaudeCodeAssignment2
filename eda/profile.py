"""
Schema, missingness, distribution-shape, and outlier profiling for the three raw sources.

Every function here should return something concrete an evaluator (or
`scripts/verify_findings.py`) can check against the real data — not a prose-only summary.
"""

import pandas as pd

SKEW_THRESHOLD = 0.5


def profile_schema(df: pd.DataFrame) -> dict:
    """Return the columns, dtypes, and row count of the given frame."""
    return {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "n_rows": int(len(df)),
    }


def profile_missingness(df: pd.DataFrame) -> dict:
    """Return per-column null counts.

    Do not conflate a customer legitimately absent from transactions.db (zero activity) with
    an actually-missing value in a column that IS present — see `count_zero_activity_customers`
    below for the former.
    """
    return {col: int(n) for col, n in df.isna().sum().items()}


def count_zero_activity_customers(customers: pd.DataFrame, transactions: pd.DataFrame) -> int:
    """Count customers with zero matching rows in `transactions` (computed, not hardcoded)."""
    if customers.empty:
        raise ValueError("count_zero_activity_customers: customers frame is empty")
    return int((~customers["customer_id"].isin(transactions["customer_id"])).sum())


def profile_distribution(series: pd.Series) -> dict:
    """Return mean, median, skewness, skew direction, and range for a numeric column.

    Skew direction comes from the sample skewness statistic: |skew| below SKEW_THRESHOLD is
    "roughly symmetric", otherwise the sign of the skew decides "right" or "left".
    """
    values = series.dropna()
    if values.empty:
        raise ValueError("profile_distribution: no non-null values to profile")
    skew = float(values.skew())
    if abs(skew) < SKEW_THRESHOLD:
        direction = "roughly symmetric"
    else:
        direction = "right" if skew > 0 else "left"
    return {
        "n": int(values.shape[0]),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "skew": skew,
        "skew_direction": direction,
        "min": float(values.min()),
        "max": float(values.max()),
    }


def count_outliers(series: pd.Series, rule: str = "iqr", multiplier: float = 1.5) -> dict:
    """Count values outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR] (Tukey fences).

    Only the "iqr" rule is implemented; any other rule name raises ValueError so an unstated
    rule can never silently be used.
    """
    if rule != "iqr":
        raise ValueError(f"Unsupported outlier rule: {rule!r}")
    values = series.dropna()
    if values.empty:
        raise ValueError("count_outliers: no non-null values to test")
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - multiplier * iqr, q3 + multiplier * iqr
    return {
        "rule": f"iqr x{multiplier}",
        "bound_low": float(low),
        "bound_high": float(high),
        "n_outliers": int(((values < low) | (values > high)).sum()),
    }
