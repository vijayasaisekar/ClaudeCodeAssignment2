# ARTIFACT_NOTES.md — self-critique log

## What was wrong or reconsidered (and what changed)

1. **Stage 0 read amount as roughly normal.** Checked: mean 49.72, median 33.82, skew 6.11.
   Corrected to median/IQR, and no t-test on amount. (eda_review.md, distribution section)
2. **Stage 0 counted the 81 zero-activity customers as "missing transaction data".** Checked:
   zero rows, no nulls in any column, and all 81 are churned by the label. Reported as a
   zero-activity population.
3. **Stage 0 called days_since_last_txn the strongest predictor.** It is circular with the label
   (churned customers have at least 91 days since last purchase; trailing spend is 0 for all 202
   churned). Flagged, excluded, and kept only as a diagnostic.
4. **Label boundary.** My first implementation used a 90×24h window. It reproduces only 1499 of 1500
   labels; customer 697 (last purchase 90.3 days before as-of) is labelled not churned. The label
   is whole days since last purchase exceeding 90, which matches all 1500. Changed the diagnostics and
   the claim check to that rule. The 24h-window mismatch is logged in DATA_ISSUES.md.
5. **Label-eligibility artifact missed by Stage 0.** 100 customers signed up inside the window, and
   47% of them are churned without ever having had a chance to buy. Driver tests use only the
   1400 customers who signed up before the window.
6. **Multi-source agreement was assumed by Stage 0 and is false for 2026-07.** Reaggregating
   transactions.db to (customer_id, month) shows 237 fewer transactions in the parquet (994 vs 1231),
   102 customer-months missing entirely from the extract, and 110 customer-months with different
   counts. Earlier months match exactly.
7. **Test choice.** Pre-window transaction count and spend are zero-heavy and right-skewed, so
   Mann-Whitney U rather than a t-test. Categorical drivers use chi-square with Cramér's V.
8. **Null results reported.** Channel (p = 0.0948) and region (p = 0.0863) are not significant and are
   reported as null, not dropped.
9. **p-value display.** The days-since-last Mann-Whitney p-value is 3.7e-74 exactly. The notebook's
   round(v, 4) displayed it as 0.0; the docs state p < 0.0001, which is what the code confirms.

## Checks run and results

- **Independent spot-check (raw pandas, not eda/):** churn rate 0.1347 (202/1500); zero-activity
  count 81. Both match EDA_FINDINGS.md. `scripts/verify_findings.py` computes these with plain
  pandas and sqlite, not the eda/ modules.
- **verify_findings.py:** 81 tagged claims across EDA_FINDINGS.md, MODEL_RECOMMENDATION.md and
  DATA_ISSUES.md; all pass (`verify_findings_output.txt`).
- **Mutation check (manual, scratch copy):** changed churn_rate from 0.1347 to 0.1400 in EDA_FINDINGS.md.
  verify_findings reports `FAIL EDA_FINDINGS.md churn_rate: stated 0.1400, recomputed 0.1346...` and exits 1
  (`mutation_check_output.txt`). The same check runs automatically in
  `tests/test_findings_reproduce.py::test_mutated_number_is_caught`.
- **Notebook:** executed top to bottom in the `churn-eda` kernel; 0 error outputs.
- **pytest:** 22 passed (`pytest_output.txt`).
- **Leakage re-check:** flag function flags exactly days_since_last_txn and trailing_90d_spend;
  pre_window_*, region, acquisition_channel and tenure_days are not flagged.
- **Post-as-of guard:** the source has 0 rows at/after 2026-08-01 (max timestamp 2026-07-31 23:50).

## Limitations

- The build was done in one session by the same agent that wrote Stage 0 and the review. The
  reconciliation step was not run as an independent review, so the review is not independently
  checked by a second model or a person.
- The Tiger OS workflow and generated skill files were not produced. The skill is the provided
  skill.md plus its Domain Context section.
- Trailing-window and zero-activity handling assumes the label rule above. If the upstream label
  is defined differently, the leakage and eligibility sections need to be re-derived.
- tenure_days is in the leakage candidate list but was not hypothesis-tested.

