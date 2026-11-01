# Stage 0 — first-pass drafts (AI-generated, NOT verified)

Generated directly from data/customers.csv, data/transactions.db and
data/transactions_monthly_agg.parquet with skill.md as provided (no Domain Context, no
eda_review.md). Best-effort inference, not an authoritative analysis. Confidence flags are
on each claim. This file is kept as the raw material the learner's review corrects in
eda_review.md; it is intentionally not corrected here.

## EDA_FINDINGS_DRAFT.md

- Customers: 1,500 rows, no nulls in any column. [high confidence]
- Churn: 202 churned, churn rate 13.5%. [high confidence]
- Zero-activity: 81 customers have no rows in transactions.db, i.e. about 5.4% of the base
  with missing transaction data. [medium confidence — "missing" wording not checked]
- Amount: mean 49.72, std 55.24; looks roughly normal, so mean/std are representative.
  [low confidence — shape not tested numerically]
- Outliers: a few high-value transactions (max 1,684.21). [low confidence — no rule applied]
- Channel: organic churns more (15.3%) than paid_search (10.2%). [low confidence — eyeballed
  from a bar chart, no test run]
- Monthly volume: transaction counts rise month over month from 2024-02 to 2026-07.
  [medium confidence — direction not tested for monotonicity]
- Multi-source: transactions.db and the monthly parquet agree; total amount is in the same
  range in both. [low confidence — not reaggregated month by month]

## DATA_ISSUES_DRAFT.md

- Candidate leakage: days_since_last_txn separates churned and non-churned customers almost
  perfectly (Mann-Whitney p ≈ 4e-74). Treated as the single strongest predictor. Trailing
  90-day spend is 0 for every churned customer and positive for most others, also a strong
  predictor. [high confidence in the numbers; interpretation not checked]
- Class imbalance: 13.5% positive, moderate. A model reaching ~86.5% accuracy by predicting
  "not churned" is a sensible baseline to beat.
- Non-stationarity: volume grows, so a random train/test split should be fine.

## MODEL_RECOMMENDATION_DRAFT.md

- Candidate: gradient-boosted trees over all available columns, including days_since_last_txn
  and trailing 90-day spend, which are the top features by separation. Accuracy as the
  headline metric. [medium confidence — chosen because of the strong separation above]
- Alternative: logistic regression. Not chosen because it may underfit the separation.
