"""
Leakage-discipline checks specific to this dataset's label definition: churn = no purchase
in the 90 days before the as-of date.

A feature computed over a window that overlaps that same trailing period is not merely
correlated with the label — it is circular with it. These checks exist to catch that
specifically, not to raise a generic "be careful about leakage" warning.

Windows are expressed as half-open intervals of whole days before the as-of date:
(lo, hi) covers transactions with  as_of - hi <= txn_timestamp < as_of - lo.
A driver with window None is a static customer attribute (not derived from transactions).
"""

import numpy as np
import pandas as pd
from scipy import stats

AS_OF = pd.Timestamp("2026-08-01")
LABEL_WINDOW_DAYS = 90
LABEL_WINDOW = (0, LABEL_WINDOW_DAYS)

# Window each candidate driver is computed over, per eda_review.md. Keep in sync with the
# driver definitions in eda/hypotheses.py.
DRIVER_WINDOWS = {
    "acquisition_channel": None,
    "region": None,
    "tenure_days": None,
    "pre_window_txn_count": (LABEL_WINDOW_DAYS, np.inf),
    "pre_window_spend": (LABEL_WINDOW_DAYS, np.inf),
    "days_since_last_txn": (0, np.inf),
    "trailing_90d_spend": (0, LABEL_WINDOW_DAYS),
}


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def flag_label_circular_drivers(candidate_drivers: list[str]) -> dict:
    """Flag candidate drivers whose computation window overlaps the label's trailing window.

    Returns {"flagged": {driver: reason}, "not_flagged": [...], "unclassified": [...]}.
    A driver not in DRIVER_WINDOWS is "unclassified" rather than silently passed.
    """
    flagged, not_flagged, unclassified = {}, [], []
    for driver in candidate_drivers:
        if driver not in DRIVER_WINDOWS:
            unclassified.append(driver)
            continue
        window = DRIVER_WINDOWS[driver]
        if window is not None and _overlaps(window, LABEL_WINDOW):
            span = "all history before as-of" if np.isinf(window[1]) else f"the last {window[1]} days before as-of"
            flagged[driver] = (
                f"computed over {span}, which overlaps the label's own trailing "
                f"{LABEL_WINDOW_DAYS}-day window; circular with the label"
            )
        else:
            not_flagged.append(driver)
    return {"flagged": flagged, "not_flagged": not_flagged, "unclassified": unclassified}


def label_window(as_of: pd.Timestamp = AS_OF) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return (start, end) of the label's trailing 90-day window: [start, end)."""
    return as_of - pd.Timedelta(days=LABEL_WINDOW_DAYS), as_of


def eligible_customers(customers: pd.DataFrame, as_of: pd.Timestamp = AS_OF) -> pd.DataFrame:
    """Customers who had signed up before the label window opened.

    A customer who signed up inside the window cannot have bought "before" it, so the label
    marks them churned by construction; they are excluded from driver testing (see
    DATA_ISSUES.md).
    """
    start, _ = label_window(as_of)
    return customers[customers["signup_date"] < start].copy()


def check_no_post_as_of_rows_used(transactions: pd.DataFrame, as_of: str) -> dict:
    """Confirm no row with txn_timestamp at or after `as_of` is in the frame passed in.

    Pass the frame your computations actually used. The source file may contain later rows;
    the check is that your own computations excluded them.
    """
    cutoff = pd.Timestamp(as_of)
    n_post = int((transactions["txn_timestamp"] >= cutoff).sum())
    return {
        "passed": n_post == 0,
        "n_post_as_of_rows_in_source": n_post,
        "note": f"rows at/after {as_of} present in the frame used for computation: {n_post}",
    }


def trailing_window_diagnostics(customers: pd.DataFrame, transactions: pd.DataFrame,
                                as_of: pd.Timestamp = AS_OF) -> dict:
    """Quantify how well the trailing-window variables separate churned customers.

    Reported only to show the circularity: a near-perfect separation here is the label
    restated, not predictive power. These variables are excluded from modelling.
    """
    start, end = label_window(as_of)
    before_end = transactions[transactions["txn_timestamp"] < end]
    last_txn = before_end.groupby("customer_id")["txn_timestamp"].max()
    # Whole days elapsed: the label rule is "more than 90 whole days since last purchase".
    days_since_last = (end - customers["customer_id"].map(last_txn)).dt.days
    in_window = transactions[(transactions["txn_timestamp"] >= start)
                             & (transactions["txn_timestamp"] < end)]
    spend_90d = customers["customer_id"].map(in_window.groupby("customer_id")["amount"].sum())
    spend_90d = spend_90d.fillna(0.0)

    churned = customers["churned"].to_numpy() == 1
    dsl = days_since_last.dropna()
    churned_dsl = days_since_last[churned].dropna()
    not_churned_dsl = days_since_last[~churned].dropna()
    mwu = stats.mannwhitneyu(churned_dsl, not_churned_dsl, alternative="two-sided")
    return {
        "days_since_last_txn_min_churned": float(churned_dsl.min()),
        "days_since_last_txn_max_not_churned": float(not_churned_dsl.max()),
        "days_since_last_txn_mwu_p": float(mwu.pvalue),
        "days_since_last_txn_n_nonnull": int(dsl.shape[0]),
        "trailing_90d_spend_max_churned": float(spend_90d[churned].max()),
        "trailing_90d_spend_min_not_churned": float(spend_90d[~churned].min()),
    }
