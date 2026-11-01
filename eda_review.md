# eda_review.md — Churn EDA & Model-Family Recommendation

Review of Stage 0's first-pass drafts (`outputs/artifacts/stage0/stage0_drafts.md`), checked
against the raw sources and against skill.md's Domain Context section. Every number below was
recomputed from `data/` (see `scripts/` and `outputs/artifacts/`). - Learner Verified

## Distribution / missingness / outlier corrections

- **Correction (amount shape)**: Stage 0 said `amount` "looks roughly normal, so mean/std are
  representative" (mean 49.72, std 55.24). Checked: median is 33.82, skew is 6.11, max is
  1,684.21 against a 75th percentile of 61.39. This is strongly right-skewed. Monetary
  summaries use median and IQR; any t-test on amount is rejected.
- **Correction (outlier rule)**: Stage 0 said "a few high-value transactions" with no rule.
  Stated rule: Tukey fences, Q1 − 1.5·IQR to Q3 + 1.5·IQR, giving [−46.18, 125.93]. That
  flags 783 of 11,742 transactions (6.7%). This is a heavy right tail, not a few outliers.
  Kept in the data; not removed.
- **Correction (zero-activity is not missing)**: Stage 0 said "81 customers (5.4%) with
  missing transaction data". They have no rows in `transactions.db`, which is zero activity,
  not a null. Checked: all 81 have `churned = 1`, and 47 of them signed up inside the label
  window (see Leakage). Reported as a zero-activity population, and their churn status is
  explained by the label definition rather than by any transaction pattern.
- **Correction (null-free claim)**: Stage 0 said there were no nulls. Confirmed for all three
  sources (customers, transactions, monthly_agg: zero nulls in every column), but the 81
  zero-activity customers are a row-count gap across sources, not a null in any column.

## Hypothesis tests to run

Population for every test: the **eligible** customers, meaning those who signed up before
2026-05-03 (the label window's start). N = 1,400, churned = 155 (11.07%). Customers who signed
up inside the window are excluded (see Leakage).

- **Driver**: acquisition_channel (4 levels)
  - **Test**: chi-square test of independence (vs churned)
  - **Why this test**: categorical driver against a binary outcome; no ordering assumed.
    Reported with Cramér's V (effect size). Result: chi2 = 6.37, df = 3, p = 0.095, V = 0.067.
    **Null at alpha 0.05.** Churn by channel: organic 12.9%, social 12.9%, referral 10.9%,
    paid_search 7.9%. The gap looks large but is not significant with this sample.
- **Driver**: region (4 levels)
  - **Test**: chi-square test of independence (vs churned)
  - **Why this test**: categorical, same as channel. Result: chi2 = 6.59, df = 3, p = 0.086,
    V = 0.069. **Null at alpha 0.05.** Churn by region: east 14.7%, north 9.6%, south 9.9%,
    west 10.0%.
- **Driver**: pre_window_txn_count (transactions before 2026-05-03; zero for 16.4% of customers)
  - **Test**: Mann-Whitney U (two-sided)
  - **Why this test**: a count with heavy zeros and right skew (skew 0.79). A t-test's
    normality assumption fails. Result: U = 85,979, p = 0.026, rank-biserial r = −0.11
    (churned customers have fewer pre-window transactions: median 4 vs 5). **Significant,
    small effect.**
- **Driver**: pre_window_spend (sum of amounts before 2026-05-03; zero for 16.4%)
  - **Test**: Mann-Whitney U (two-sided)
  - **Why this test**: right-skewed money (skew 1.25) with zeros. Result: U = 85,665,
    p = 0.022, rank-biserial r = −0.11 (median 187.55 for churned vs 238.00 for not churned).
    **Significant, small effect.** This is a legitimate driver: computed only from transactions
    before the label window.

Reviewed but not tested:
- **tenure_days**: a static attribute of signup date, not computed over the label window, so
  it passes the leakage check. Not tested in this build to keep the driver list short.

## Leakage / imbalance / non-stationarity / multi-source flags

- **Leakage**: **days_since_last_txn** and **trailing_90d_spend** are leakage-tainted.
  - Why: the label is "no purchase in the 90 days before 2026-08-01". Checked against the
    data: a customer is churned iff whole days elapsed since their last transaction exceed 90
    (zero-activity customers count as churned). That matches 1,500 of 1,500 customers. A plain
    90×24h window reproduces this for 1,499 customers; the one exception is customer 697 (last
    transaction 2026-05-02 17:12, 90.3 days before as-of, labelled not churned), a boundary
    case logged in DATA_ISSUES.md. Both features below are computed over that same window. A churned customer has, by definition, no transaction in it, so
    trailing spend is 0 for them, and days-since-last is at least 91 for them.
  - Evidence: churned customers have days_since_last_txn ≥ 91 and trailing_90d_spend = 0 for
    all 202 churned customers; not-churned customers have days_since_last_txn ≤ 90 (MWU
    p < 0.0001). This separation is the label restated, not predictive power.
  - Stage 0 called days_since_last_txn "the strongest predictor". I'm rejecting that
    interpretation. These variables are excluded from modelling and from the recommendation.
  - **Label-eligibility artifact (not in Stage 0)**: 100 customers signed up inside the 90-day
    window (2026-05-03 onward), and 47% of them are churned. A customer who signed up on
    2026-06-15 and has not bought yet is labelled churned, which is an artifact of the label
    definition rather than a churn event. Excluded from driver testing and from modelling. The
    churn rate reported below is the overall rate, with the eligible rate alongside.
  - Zero-activity customers: all 81 churned, which is also the label by construction. Not used
    as a feature.
- **Imbalance**: overall churn rate is 13.47% (202 of 1,500). Eligible rate is 11.07% (155 of
  1,400). A model that always predicts "not churned" gets accuracy 86.53% (overall) and
  88.93% (eligible), so accuracy is misleading. Use PR-AUC, precision and recall on the churned
  class at a stated threshold, and recall or lift in the top-decile of predicted risk. ROC-AUC
  is acceptable as a secondary metric.
- **Non-stationarity**: confirmed. Monthly transaction count rises from 1 (2024-02) to 1,231
  (2026-07). Slope +41.0 rows per month; Spearman rho = 0.998 (p ≈ 2e-34), so the trend is
  monotonic, not noise. A random train/test split would put future-period behaviour into
  training and would make validation optimistic. Use a time-based split: train on earlier
  as-of dates and validate on later ones.
- **Multi-source**: **Stage 0 said the sources agree; that was not checked.** Reaggregating
  transactions.db to (customer_id, month) and comparing against the parquet extract:
  - Months 2024-02 to 2026-06 match exactly (all customer-months, counts and amounts).
  - **2026-07 does not match.** Row-level has 1,231 transactions and 62,084.62 total; the
    extract has 994 and 50,116.67. Gap: 237 transactions (19.3% of July), 11,967.95 in amount,
    and 102 customer-months present only in the row-level table; another 110 customer-months
    appear in both with different counts. The extract's July is
    incomplete.
  - Comparison function: `eda/time_checks.compare_row_level_vs_monthly_agg`. A real disagreement
    shows up as nonzero customer-months-only-in-one-source or count/amount mismatch in a
    specific month, and that is what is reported.

## Model-family judgment

- **Candidate family**: regularized logistic regression (L2, class-weighted) as the primary
  model, on the eligible population, using only pre-window features (transaction count,
  spend, channel, region, and a log-transform for the right-skewed money). Validated
  out-of-time, not randomly.
- **Why, tied to this dataset's checked characteristics**: only 155 churned eligible customers,
  and the only significant drivers are two weak pre-window behavioural effects (r ≈ −0.11).
  The categorical drivers are null. With that little signal and 155 positives, a model with
  many parameters would fit noise. Logistic regression is interpretable for a retention team,
  which the weak signal makes necessary. Accuracy is replaced with PR-AUC and top-decile lift.
- **Alternative considered**: gradient-boosted trees (e.g. LightGBM) — **Why not the top pick**:
  with about 1,400 rows and 155 positives, boosting overfits and loses interpretability, and the
  extra capacity has no signal to exploit in these four usable drivers. Revisit only if more
  pre-window features with real signal become available.
- **Drivers assumed usable**: pre_window_txn_count, pre_window_spend (both significant, computed
  before the window); acquisition_channel and region (kept as candidates, not significant).
- **Drivers excluded**: days_since_last_txn and trailing_90d_spend (label-circular, see
  Leakage); signup-in-window / eligibility (label artifact, excluded from the population).
  Zero-activity status is excluded as a feature because it is the label restated.
