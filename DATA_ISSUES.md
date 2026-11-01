# DATA_ISSUES.md — leakage, imbalance, non-stationarity, multi-source

Each flag is backed by a tagged number, recomputed by `python -m scripts.verify_findings`.

## 1. Leakage (label circularity) — HIGH

- **days_since_last_txn** and **trailing_90d_spend** are computed over the label's own trailing
  90-day window. They restate the label; they do not predict it.
  - Churned customers' minimum days since last transaction: 91<!--c:churned_min_days_since_last-->.
  - Maximum trailing 90-day spend among churned customers: 0.00<!--c:churned_max_trailing_90d_spend-->.
  - Action: excluded from modelling (see MODEL_RECOMMENDATION.md).

## 2. Label definition boundary — MEDIUM

- The label is whole days since last purchase exceeding 90. It matches all 1500<!--c:label_rule_match_count--> customers.
- A plain 90×24h window (no purchase in [2026-05-03 00:00, 2026-08-01)) reproduces only
  1499<!--c:window_24h_match_count--> of 1500. The exception is customer 697: last purchase
  2026-05-02 17:12, a little over 90 days before the as-of date, labelled not churned.
- Action: the label is used as given. Any future feature window must use the same whole-day rule,
  not a 90×24h window, or it will disagree with the label for boundary customers.

## 3. Zero-activity customers and label eligibility — HIGH

- Zero-activity customers (no rows in transactions.db): 81<!--c:zero_activity_count-->. All are churned
  (<!--c:zero_activity_churned_count-->81). This is zero activity, not missing data, and it is the label restated.
- Customers who signed up inside the 90-day window: 100<!--c:signup_in_window_n-->, with churn rate 0.47<!--c:signup_in_window_churn_rate-->.
  The label marks them churned before they had a chance to buy. This is an eligibility artifact.
- Action: driver testing and modelling use the eligible population (signed up before 2026-05-03):
  1400<!--c:eligible_n--> customers.

## 4. Class imbalance — MEDIUM

- Overall churn rate: 0.1347<!--c:churn_rate--> (202<!--c:churned_count--> of 1500<!--c:n_customers-->).
- Eligible churn rate: 0.1107<!--c:eligible_churn_rate-->; 155<!--c:eligible_churned_count--> churned customers.
- Always-"not churned" baseline accuracy: 0.8653<!--c:baseline_accuracy--> overall and
  0.8893<!--c:eligible_baseline_accuracy--> on the eligible population. Accuracy is ruled out as a headline metric.
- Use PR-AUC, precision and recall on the churned class, and top-decile lift.

## 5. Non-stationarity (time drift) — HIGH

- Monthly transaction count rises across 30<!--c:n_months--> months, with a slope of +41.0<!--c:trend_slope_per_month--> transactions per month.
  Spearman rho 0.998<!--c:trend_spearman_rho--> (monotonic).
- Action: do not use a random train/test split. Use a time-based split and validate on later as-of dates.

## 6. Multi-source disagreement (row-level vs monthly parquet) — HIGH

- Reaggregated transactions.db to (customer_id, month) and compared with transactions_monthly_agg.parquet.
- Months with any disagreement: 1<!--c:months_with_source_disagreement-->, all in 2026-07.
- 2026-07 row-level: 1231<!--c:july_2026_db_txn_count--> transactions. Extract: 994<!--c:july_2026_pq_txn_count-->.
  Gap: 237<!--c:july_2026_txn_gap-->. Customer-months only in the row-level table: 102<!--c:july_2026_db_only_customer_months-->.
  Customer-months in both sources with a different count: 110<!--c:july_2026_count_mismatch_customer_months-->.
  Amount gap: 11967.95<!--c:july_2026_amount_gap-->.
- Action: the extract's July 2026 is incomplete. Use transactions.db for July 2026, or confirm a
  fixed extract before any feature uses the parquet for the latest month. Earlier months agree exactly.

## 7. Outliers and skew — LOW (informational)

- transactions.db `amount`: 783<!--c:amount_outlier_count--> rows outside the Tukey fences; upper fence 125.93<!--c:amount_upper_fence-->.
  Mean 49.72<!--c:amount_mean--> vs median 33.82<!--c:amount_median-->, skewness 6.11<!--c:amount_skew-->.
  Kept in the data. Use robust summaries and log transforms.

## Source files

Not edited. All three files were read-only in this analysis (`mode=ro` for SQLite).
