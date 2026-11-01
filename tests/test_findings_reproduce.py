"""
The test that matters most for this assignment: proves every numeric claim stated in the
findings documents actually reproduces from the raw data, rather than being merely asserted.

Claims are checked by scripts/verify_findings.py. These tests check each claim family
separately so a failure names the family, and one test mutates a stated number to prove the
check catches a wrong value.
"""

import shutil
from pathlib import Path

from scripts import verify_findings as vf

FINDINGS_DIR = Path(".")


def _failures_for(*prefixes: str) -> list[str]:
    failures = vf.check_findings([FINDINGS_DIR / "EDA_FINDINGS.md"])
    return [f for f in failures if any(f" {p}" in f for p in prefixes)]


def test_churn_rate_claim_reproduces():
    assert _failures_for("churn_rate", "churned_count", "n_customers") == []


def test_zero_activity_count_claim_reproduces():
    assert _failures_for("zero_activity_count", "zero_activity_churned_count") == []


def test_each_hypothesis_result_reproduces():
    assert _failures_for("channel_chi2_p", "region_chi2_p", "pre_txn_count_mwu_p",
                         "pre_spend_mwu_p", "pre_spend_rank_biserial",
                         "channel_cramers_v", "region_cramers_v") == []


def test_multi_source_gap_claim_reproduces():
    assert _failures_for("july_2026", "months_with_source_disagreement") == []


def test_all_stated_findings_reproduce_across_documents():
    assert vf.check_findings() == []


def test_mutated_number_is_caught(tmp_path):
    """A wrong stated number must fail verification; a copy keeps the real file untouched."""
    scratch = tmp_path / "EDA_FINDINGS.md"
    shutil.copy(FINDINGS_DIR / "EDA_FINDINGS.md", scratch)
    text = scratch.read_text(encoding="utf-8")
    mutated = text.replace("0.1347<!--c:churn_rate-->", "0.1400<!--c:churn_rate-->", 1)
    assert mutated != text
    scratch.write_text(mutated, encoding="utf-8")
    failures = vf.check_findings([scratch])
    assert any("churn_rate" in f for f in failures)
