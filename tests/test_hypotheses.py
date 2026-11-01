"""
Hypothesis-function tests against constructed input with a known answer, in both directions.
"""

import numpy as np
import pandas as pd

from eda import hypotheses


def _frame(driver_values, churned, driver):
    return pd.DataFrame({driver: driver_values, "churned": churned})


def test_hypothesis_detects_engineered_difference():
    rng = np.random.default_rng(0)
    n = 400
    churned = np.repeat([0, 1], n // 2)
    spend = np.where(churned == 1, rng.gamma(1.0, 5.0, n), rng.gamma(4.0, 60.0, n))
    frame = _frame(spend, churned, "pre_window_spend")
    result = hypotheses.test_pre_window_spend(frame)
    assert result["test"].startswith("Mann-Whitney")
    assert result["p_value"] < 0.001
    assert result["higher_group"] == "not_churned"
    assert result["effect_size_or_magnitude"] < 0


def test_hypothesis_reports_null_result_honestly():
    rng = np.random.default_rng(1)
    n = 800
    churned = rng.integers(0, 2, n)
    channel = rng.choice(["organic", "social", "referral", "paid_search"], n)
    frame = _frame(channel, churned, "acquisition_channel")
    result = hypotheses.test_acquisition_channel(frame)
    assert result["test"].startswith("chi-square")
    assert result["p_value"] > 0.05
    assert 0 <= result["effect_size_or_magnitude"] < 0.1
    assert result["n"] == n


def test_hypothesis_uses_test_matching_variable_shape():
    rng = np.random.default_rng(2)
    n = 300
    churned = np.repeat([0, 1], n // 2)
    region = rng.choice(["east", "north", "south", "west"], n)
    region_result = hypotheses.test_region(_frame(region, churned, "region"))
    assert region_result["test"].startswith("chi-square")
    assert region_result["higher_group"] is None
    assert region_result["highest_churn_group"] in {"east", "north", "south", "west"}
    spend_result = hypotheses.test_pre_window_spend(_frame(rng.gamma(1.0, 3.0, n), churned, "pre_window_spend"))
    assert spend_result["test"].startswith("Mann-Whitney")

def test_hypothesis_rejects_constant_driver_explicitly():
    """A driver with one level has no test to run; it must raise, not return p=1.0."""
    import pytest

    frame = _frame(["east"] * 50, [0, 1] * 25, "region")
    with pytest.raises(ValueError):
        hypotheses.test_region(frame)
