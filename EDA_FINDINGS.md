# EDA_FINDINGS.md — verified findings

Every number below is tagged with a claim ID and recomputed from `data/` by
`python -m scripts.verify_findings` (also run by `tests/test_findings_reproduce.py`). Source
of truth for the analysis: `eda/`, `scripts/run_*.py`, and `notebooks/eda_churn.ipynb`.
Corrections to Stage 0 are recorded in `eda_review.md`.

As-of date: 2026-08-01. Label: no purchase in the 90 days before the as-of date, implemented
as whole days since the last transaction exceeding 90, with zero-activity customers churned.

## 1. Schema, missingness, zero-activity

- customers (`customer_id`, `signup_date`, `acquisition_channel`, `region`, `churned`): 1500<!--c:n_customers--> rows, with zero nulls.
- transactions.db (table `transactions`): 11742<!--c:txn_rows--> rows, with zero nulls.
- transactions_monthly_agg.parquet: 8086<!--c:monthly_rows--> rows, with zero nulls in every column.
- Churned: 202<!--c:churned_count--> customers (churn rate 0.1347<!--c:churn_rate-->).
- Zero-activity customers (no rows in `transactions.db`): 81<!--c:zero_activity_count-->. All 81 are churned (<!--c:zero_activity_churned_count-->81). This is zero activity, not missing data: no column is null for them.
- Label-rule check: the whole-day rule ("churned iff last purchase more than 90 days before as-of, or never purchased") matches 1500<!--c:label_rule_match_count--> of 1,500 customers.

## 2. Amount distribution and outliers (transactions.db `amount`)

- Mean 49.72<!--c:amount_mean--> vs median 33.82<!--c:amount_median-->; skewness 6.11<!--c:amount_skew-->, right-skewed. Use median and IQR for monetary summaries.
- Outlier rule: Tukey fences, Q1 − 1.5·IQR to Q3 + 1.5·IQR. Upper fence 125.93<!--c:amount_upper_fence-->. Rows outside the fences: 783<!--c:amount_outlier_count--> of 11742<!--c:txn_rows-->. They are kept, not removed.

## 3. Eligible population and label artifact

- Eligible for driver testing: customers who signed up before 2026-05-03. N = 1400<!--c:eligible_n-->; churn rate 0.1107<!--c:eligible_churn_rate-->.
- Signed up inside the label window: 100<!--c:signup_in_window_n--> customers, with churn rate 0.47<!--c:signup_in_window_churn_rate-->. The label marks them churned because they have not had time to buy. Excluded from testing (DATA_ISSUES.md).

## 4. Hypothesis tests (eligible population)

| Driver | Test | p-value | Effect | Result |
|---|---|---|---|---|
| acquisition_channel | chi-square of independence | 0.0948<!--c:channel_chi2_p--> | Cramér's V 0.067<!--c:channel_cramers_v--> | null |
| region | chi-square of independence | 0.0863<!--c:region_chi2_p--> | Cramér's V 0.069<!--c:region_cramers_v--> | null |
| pre_window_txn_count | Mann-Whitney U | 0.0263<!--c:pre_txn_count_mwu_p--> | — | significant |
| pre_window_spend | Mann-Whitney U | 0.0223<!--c:pre_spend_mwu_p--> | rank-biserial -0.112<!--c:pre_spend_rank_biserial--> | significant, small effect |

Reading: churned customers have slightly less pre-window spend (lower value is higher churn). Two categorical drivers are null; those nulls are reported, not dropped.

## 5. Leakage-tainted trailing-window drivers (diagnostic only, excluded from modelling)

- days_since_last_txn: churned customers' minimum is 91<!--c:churned_min_days_since_last--> days. Not-churned customers have at most 90 days. Mann-Whitney p <0.0001<!--c:dsl_mwu_p_below-->. Separation is the label restated, not predictive power.
- trailing_90d_spend: maximum among churned customers is 0.00<!--c:churned_max_trailing_90d_spend-->. Circular with the label.

## 6. Monthly transaction volume (non-stationarity)

- Monthly txn_count rises from 2024-02 to 2026-07 (30<!--c:n_months--> months).
- OLS slope +41.0<!--c:trend_slope_per_month--> transactions per month. Spearman rho 0.998<!--c:trend_spearman_rho-->, so the trend is monotonic. A random split is not safe; use a time-based split.

## 7. Multi-source agreement (row-level vs monthly extract)

- Reaggregated transactions.db to (customer_id, month) and compared with the parquet extract, month by month. Months with any disagreement: 1<!--c:months_with_source_disagreement-->.
- 2026-07: row-level has 1231<!--c:july_2026_db_txn_count--> transactions; the extract has 994<!--c:july_2026_pq_txn_count-->. Gap: 237<!--c:july_2026_txn_gap-->. Customer-months present only in the row-level table: 102<!--c:july_2026_db_only_customer_months-->. Customer-months present in both sources with a different count: 110<!--c:july_2026_count_mismatch_customer_months-->. Amount gap: 11967.95<!--c:july_2026_amount_gap-->.
- All earlier months match exactly on count and amount for every customer-month.
