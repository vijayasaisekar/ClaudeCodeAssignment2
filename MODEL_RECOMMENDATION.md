# MODEL_RECOMMENDATION.md

## Recommendation

**Primary: regularized (L2) logistic regression, class-weighted, trained on the eligible
population (customers who signed up before the label window opened), using only features
computed before the window.** Validate out-of-time, not with a random split. Report PR-AUC,
precision and recall on the churned class at a stated threshold, and lift in the top decile of
predicted risk. Do not report accuracy as a headline metric.

The recommendation is driven by the checked characteristics of this data:

1. **Small positive class on the usable population.** The eligible population has 1400<!--c:eligible_n--> customers,
   and 0.1107<!--c:eligible_churn_rate--> of them churned. Few positives mean a high-capacity model
   fits noise.
2. **Weak signal in the usable drivers.** The only significant drivers are two pre-window
   behavioural measures, each with a small effect: pre-window spend (p = 0.0223<!--c:pre_spend_mwu_p-->,
   rank-biserial -0.112<!--c:pre_spend_rank_biserial-->). Both categorical drivers are null: channel
   (p = 0.0948<!--c:channel_chi2_p-->) and region (p = 0.0863<!--c:region_chi2_p-->). A linear model with few
   parameters matches this signal level.
3. **Skewed money and count features.** Pre-window spend is strongly right-skewed on the eligible
   population, with many zero-spend customers. A log transform keeps a linear model well-behaved.
4. **Time drift.** Monthly volume grows monotonically (Spearman 0.998<!--c:trend_spearman_rho-->), so validation must be out of time.
5. **Interpretability for a retention team.** A coefficient per driver lets the team see which
   behaviour raises risk.

## Alternative considered

**Gradient-boosted trees (e.g. LightGBM).** Not the top pick. With about 1400<!--c:eligible_n--> rows and 155<!--c:eligible_churned_count--> positives,
boosting overfits, and the four usable drivers offer little for it to exploit. It also gives up
the direct interpretability a retention team needs. Revisit only when more pre-window features
with real signal exist.

## Leakage-tainted variables: excluded

- **days_since_last_txn**: excluded. It is computed over the label's own 90-day window. Churned
  customers have at least 91<!--c:churned_min_days_since_last--> days, which restates the label. Its separation is
  circular, not predictive.
- **trailing_90d_spend**: excluded. Its maximum among churned customers is 0.00<!--c:churned_max_trailing_90d_spend-->,
  again the label restated.
- **Zero-activity status** (no rows in transactions.db): excluded as a feature. All 81<!--c:zero_activity_count--> zero-activity
  customers are churned, which is the label by construction.
- **Signup-in-window / eligibility**: excluded. The 100<!--c:signup_in_window_n--> customers who signed up inside the window
  are labelled churned at a 0.47<!--c:signup_in_window_churn_rate--> rate before they could buy. Modelling them would teach the
  model the label's eligibility rule.

## Drivers

- **Usable**: pre_window_spend, pre_window_txn_count (both significant, computed before the window);
  acquisition_channel and region (kept as candidates; not significant).
- **Excluded**: days_since_last_txn, trailing_90d_spend, zero-activity status, signup-in-window.

## Caveats

- The label is a single snapshot at one as-of date. Out-of-time validation needs labels at
  several earlier as-of dates; that construction belongs to the feature-pipeline work, not here.
- The multi-source gap in July 2026 (see DATA_ISSUES.md) must be resolved before any feature is
  built from the parquet extract. The row-level table is the reliable source for July.
