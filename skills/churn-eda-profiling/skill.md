
name: churn-eda-profiling description: > Runs a problem-type-appropriate exploratory data analysis on the e-commerce customer churn dataset (the same three heterogeneous sources used in the feature-pipeline assignment: a flat file, a SQL-style database, and a pre-aggregated parquet extract) and produces a verified, plain-language findings report, a defensible model-family recommendation, and a data-issues log covering leakage risk, class imbalance, and non-stationarity. Also used earlier, in a separate invocation, to generate a best-effort first-pass EDA notebook and draft findings directly from the raw sources, for the learner to review before eda_review.md is drafted. The build step requires eda_review.md to already exist alongside the raw data sources and requirements.txt — this skill implements a confirmed review, it does not originate one.
Churn EDA & Model-Family Recommendation
Purpose
You are Claude, acting as the AI notebook copilot for a DS team that is about to build a churn model for an e-commerce business, but has not yet properly characterized the data it would train on. Run the exploratory analysis end to end — profiling, hypothesis testing, time-trend and leakage diagnostics, a model-family recommendation — to a fixed production-readiness bar, implementing eda_review.md faithfully once it is confirmed.
When to Use
This skill covers two separate invocations, run at two different points in the assignment — do not conflate them.

Stage 0 — first-pass EDA notebook and draft findings. Invoke this first, before eda_review.md exists at all. Its job is to give the learner something concrete to react to and correct, not to make any judgment call on their behalf — see "Stage 0" below.

Build — the verified EDA deliverables. Use this only after the learner's eda_review.md has been independently reviewed, corrected against Stage 0's draft, and reconciled in a review conversation (see Helper Guide.docx). This stage implements a confirmed review — it does not originate one. If eda_review.md does not exist yet, stop and say so rather than drafting it yourself. Once invoked, it produces the final EDA notebook, the statistical verification scripts and tests, and the findings/recommendation/data-issues documentation in one run.
Stage 0 — Generate a first-pass EDA notebook and draft findings
Run this before anything else, directly against the raw sources — with no prior eda_review.md to lean on, since generating something to react to is the point of this stage.

Load all three raw sources (data/customers.csv, data/transactions.db, data/transactions_monthly_agg.parquet). Do not edit any of them. If the learner has provided a prior data_dictionary.md (e.g. from a companion feature-pipeline exercise on the same dataset), read it for schema context but re-derive every statistical claim in this skill's outputs from the data yourself — a schema note from another exercise is not a substitute for your own profiling.
Produce a first-pass EDA notebook (or notebook-equivalent script output) covering: schema and dtypes per source, missingness, the zero-activity customer population, distribution shape and outliers for numeric columns, category/channel/region breakdowns, churn rate overall and by candidate categorical drivers, and the monthly transaction-volume trend.
From that pass, draft EDA_FINDINGS_DRAFT.md (plain-language summary of distributions, missingness, outliers, and any apparent trend), MODEL_RECOMMENDATION_DRAFT.md (a candidate model family with reasoning), and DATA_ISSUES_DRAFT.md (candidate leakage, class-imbalance, and non-stationarity flags) — see "Domain Context" below for the bar each of these needs to clear, but do not treat it as a template to fill in mechanically.
Treat all three drafts as best-effort, not authoritative. This is inference from raw data under time pressure, not a verified analysis — say so explicitly in each draft's own text, and flag your own low-confidence claims (a distribution characterization you didn't check numerically, a "driver" you flagged from an eyeballed chart rather than a real test, a trend you asserted without checking whether it's actually monotonic) rather than presenting everything with uniform confidence. There is no fixed accuracy target to hit here — the point is that the learner's review in the next step is expected to find real things to correct, not to rubber-stamp this output. In particular, do not pre-emptively flag the recency/trailing-90-day leakage risk described in Domain Context below as an obvious, corrected finding in your own draft — a realistic first-pass EDA copilot reports a feature like "days since last transaction separates churned and non-churned customers almost perfectly" as a exciting top predictor, not as a red flag; catching that it's circular with the label definition is the learner's review to make, not yours to hand them pre-solved.
Stop here. Do not draft eda_review.md yourself — that is the learner's own step, done by reviewing and correcting these drafts (see Helper Guide.docx).

If an EDA_FINDINGS.md or DATA_ISSUES.md from an earlier phase of this same project is already present when Stage 0 runs, read it and carry its facts and open questions forward — do not regenerate from the raw sources as if no prior phase existed.
## Domain Context

This is the standard a correct EDA of this dataset must meet. Each point was checked against the raw sources (see eda_review.md and outputs/artifacts/). - Learner Verified

Distributions, missingness, outliers. A real finding states median and IQR for monetary columns. transactions.db `amount` has mean 49.72 and median 33.82 with skewness 6.11, so it is right-skewed, not normal. Outliers use the stated Tukey-fence rule (Q1 − 1.5·IQR, Q3 + 1.5·IQR), which flags 783 of 11742 rows. The 81 customers with no rows in transactions.db are zero-activity, not missing data; no column is null for them.

Hypothesis tests. Test each driver against its actual shape. Categorical drivers (acquisition_channel, region) use chi-square with Cramér's V; both are null at alpha 0.05 (p 0.0948 and 0.0863), and null results are reported. Right-skewed count and money drivers with many zeros (pre_window_txn_count, pre_window_spend) use Mann-Whitney U with rank-biserial r; both are significant but small (p 0.0263 and 0.0223, r about -0.11). Report effect size, not only the p-value.

Leakage. The label is no purchase in the 90 days before 2026-08-01, which in the data is whole days since the last transaction exceeding 90. A driver whose window overlaps that trailing 90-day window restates the label rather than predicting it. days_since_last_txn and trailing_90d_spend are circular: churned customers have at least 91 days since last purchase and zero trailing spend. A real driver is computed strictly before the window (e.g. pre-window spend) or is a static attribute (e.g. signup date). Strong separation from a window-overlapping variable is flagged, never reported as a predictor.

Class imbalance. The overall churn rate is 0.1347 (202 of 1500); the eligible rate is 0.1107 (155 of 1400). Always predicting "not churned" scores 0.8653 accuracy overall, so accuracy is not a usable headline metric. Use PR-AUC, precision and recall on the churned class, and top-decile lift.

Time drift. Monthly transaction count rises across 30 months, slope +41.0 per month, Spearman rho 0.998. The trend is monotonic. A random train/test split leaks future behaviour into training, so use a time-based split.

Multi-source agreement. transactions.db and transactions_monthly_agg.parquet must be reaggregated to (customer_id, txn_month) and compared month by month, not assumed to agree. They match exactly for 2024-02 through 2026-06. 2026-07 disagrees: 1231 row-level transactions vs 994 in the extract (gap 237, 11967.95 in amount), 102 customer-months only in row-level, and 110 customer-months with different counts. The extract's latest month is incomplete.

Model family. Characteristics that drive the choice: a small positive class (155 eligible churners), weak signal in the usable drivers (two small pre-window effects), right-skewed money features, and monotonic time drift. Primary: class-weighted L2 logistic regression on pre-window features, validated out of time. Alternative: gradient-boosted trees, not the top pick, because with about 1400 rows and 155 positives they overfit and lose interpretability. Excluded as unusable: days_since_last_txn, trailing_90d_spend, zero-activity status, and signup-in-window eligibility.

Inputs Required
For Stage 0:

data/customers.csv, data/transactions.db (SQLite, table transactions), and data/transactions_monthly_agg.parquet — provided, the raw sources. Do not edit them.
requirements.txt — provided, pins dependencies.

For the build stage:

eda_review.md — must already exist, stating the learner's corrected read of Stage 0's drafts: which distribution/outlier/missingness claims were confirmed or corrected, which candidate churn-driver hypotheses to formally test and how, the leakage/imbalance/ non-stationarity/multi-source flags to carry forward, and the model-family judgment. If it doesn't exist, stop and say so rather than originating one yourself.
requirements.txt — provided, pins dependencies (pandas, numpy, scipy, pyarrow, pytest). SQLite access uses Python's stdlib sqlite3, so it is not a separate dependency.

Workflow
Repo scaffold to create
.
├── data/customers.csv                       <- provided, do not edit
├── data/transactions.db                     <- provided, do not edit (SQLite, table `transactions`)
├── data/transactions_monthly_agg.parquet    <- provided, do not edit
├── requirements.txt                          <- provided
├── pytest.ini                                <- provided, sets pythonpath so `pytest` resolves
│                                                 `eda` imports with no extra flags needed
├── eda_review.md                            <- provided, implement faithfully
├── eda/
│   ├── __init__.py
│   ├── load.py                    <- one loader function per source, pure I/O, no analysis logic
│   ├── profile.py                 <- schema/dtype/missingness/outlier/distribution profiling functions
│   ├── hypotheses.py              <- one function per candidate churn-driver test, pure, returns stat+p+effect size
│   ├── time_checks.py             <- monthly volume trend + multi-source agreement checks
│   └── leakage_checks.py          <- as-of-date discipline + label-circularity checks
├── notebooks/
│   └── eda_churn.ipynb            <- the narrative exploratory notebook, cells runnable top to bottom
├── scripts/
│   ├── run_profile.py             <- runs eda/profile.py across all sources, prints + saves a profile summary
│   ├── run_hypothesis_tests.py    <- runs every hypothesis in eda/hypotheses.py, saves a results table
│   ├── run_time_and_leakage_checks.py  <- runs eda/time_checks.py + eda/leakage_checks.py
│   └── verify_findings.py         <- reproduces every numeric claim in EDA_FINDINGS.md from raw data, fails loudly on any mismatch
├── tests/
│   ├── test_load.py               <- source loaders: schema, row counts, dtypes
│   ├── test_profile.py            <- profiling functions on known-shape synthetic input
│   ├── test_hypotheses.py         <- each hypothesis function on constructed input with a known answer
│   ├── test_time_and_leakage_checks.py  <- trend direction, multi-source diff, leakage-flag correctness
│   └── test_findings_reproduce.py <- proves every claim in EDA_FINDINGS.md actually reproduces from raw data
├── EDA_FINDINGS.md                <- verified findings: distributions, missingness, outliers, hypothesis results, time trend, multi-source agreement
├── MODEL_RECOMMENDATION.md        <- the confirmed, defensible model-family recommendation
├── DATA_ISSUES.md                 <- verified leakage/imbalance/non-stationarity/multi-source flags
├── ARTIFACT_NOTES.md              <- self-critique log
└── review_log.md                  <- Step 3 self-review
Step 0 — Confirm the raw data loads cleanly from every source
Before implementing any analysis:

Set up a Python environment if one isn't already active, then pip install -r requirements.txt.
Load all three sources: data/customers.csv with pandas.read_csv, data/transactions.db with sqlite3.connect(...) or pandas.read_sql(...), data/transactions_monthly_agg.parquet with pandas.read_parquet. Confirm row counts and dtypes look sane for each.
Confirm the 81 zero-activity customers (customers with no rows in transactions.db) are real, by counting them directly, not assuming the number from any prior document.
Do not modify any source file. If you find what looks like a genuine data defect, note it in ARTIFACT_NOTES.md rather than silently working around it.
Step 1 — Implement the analysis modules and generate the verified findings from the review
Read eda_review.md in full, then implement it faithfully:
1a. Loaders and profiling
eda/load.py — one loader function per source, mirroring the ingestion split used in the companion feature-pipeline assignment: pure I/O, no analysis logic, so it can be unit-tested and reused independently of the profiling/hypothesis code.
eda/profile.py — schema/dtype/missingness summary per source; distribution shape (mean/median/skew direction, at minimum) and an outlier count per numeric column against a stated rule; the zero-activity customer count, computed directly, not hardcoded.
eda/hypotheses.py — one pure function per candidate churn-driver named in eda_review.md, each choosing an appropriate test for the variable's actual shape (categorical → chi-square, continuous/skewed → Mann-Whitney U, continuous/roughly normal → t-test after checking that assumption), returning the statistic, p-value, an effect size or plain-language magnitude, and which group had the higher value.
eda/time_checks.py — the monthly transaction-volume trend (from the row-level table), and the multi-source agreement check: reaggregate transactions.db to customer x month and compare against transactions_monthly_agg.parquet month by month, reporting where and by how much they diverge.
eda/leakage_checks.py — a function that flags any candidate driver in eda_review.md whose computation window overlaps the label's own trailing-90-day definition, and a function that confirms no row with txn_timestamp after the as-of date was used in any profiling or hypothesis-test computation.
1b. Scripts and notebook
scripts/run_profile.py, scripts/run_hypothesis_tests.py, scripts/run_time_and_leakage_checks.py — thin runners over the eda/ modules above, printing a human-readable summary and writing any intermediate result the notebook or EDA_FINDINGS.md generation needs.
notebooks/eda_churn.ipynb — the narrative version of the same analysis: schema and missingness review, distribution and outlier plots, churn-rate breakdowns, each hypothesis test with its result stated in a markdown cell (not just printed output with no interpretation), the time-trend plot, and the multi-source comparison plot. Every cell must run top to bottom with no manual intervention and no hidden state.
scripts/verify_findings.py — parses (or is hand-aligned with) the numeric claims stated in EDA_FINDINGS.md and recomputes each one directly from the raw sources, raising / exiting non-zero if any recomputed value doesn't match what's stated. This is the parity-test equivalent for this assignment: it exists specifically to catch a plausible but wrong number slipping into a findings document.
1c. Verified findings, recommendation, and data-issues documents
EDA_FINDINGS.md — generated from what the modules above actually compute, not restated from Stage 0's draft: schema/missingness/outlier summary per source, every hypothesis test named in eda_review.md with its real result, the time-trend characterization, and the multi-source agreement result. Every numeric claim here must be reproducible by scripts/verify_findings.py.
MODEL_RECOMMENDATION.md — the model-family recommendation confirmed in eda_review.md, restated with the actual evidence generated in this build (not Stage 0's draft reasoning), explicitly excluding or caveating any leakage-tainted candidate driver.
DATA_ISSUES.md — the leakage, class-imbalance, non-stationarity, and multi-source flags, each backed by the specific number or check that supports it (the churn rate, the trend direction/magnitude, the multi-source gap size, the named leakage-tainted variable(s)).

After generating everything above, write ARTIFACT_NOTES.md: list at least one thing you got wrong or reconsidered while building the verified analysis (a hypothesis test that needed a different test than first assumed, an outlier rule that was initially too loose/strict, a multi-source gap that was smaller or larger than Stage 0 guessed). If you genuinely produced everything cleanly, say so explicitly — but re-check the leakage-circularity flag, the zero-activity-vs-missing distinction, and that the multi-source comparison actually reaggregates the row-level table rather than trusting Stage 0's guess about it, specifically before concluding that; those are the most common gaps in a generated EDA pass like this.
Step 2 — Build the full test suite, then verify the findings yourself
Generate, across the five test files:

test_load.py — each loader against the real files: expected columns, dtypes, and a sane row-count range.
test_profile.py — the profiling functions against small constructed DataFrames with a known shape (e.g. a known skew, a known outlier, a known missingness pattern), asserting the function detects what's actually there.
test_hypotheses.py — each hypothesis function against constructed input with a known answer (e.g. two groups with a clear, engineered difference, and two groups with none), asserting the right test is used and the right conclusion is reached in both directions.
test_time_and_leakage_checks.py — the trend check against constructed monotonic vs. flat series; the multi-source check against constructed matching vs. deliberately mismatched month-level data; the leakage check against a variable that should and shouldn't be flagged.
test_findings_reproduce.py — the test that matters most for this assignment: for every numeric claim in EDA_FINDINGS.md, recompute it from the raw sources and assert it matches. If this test can't be written because a claim in EDA_FINDINGS.md isn't actually traceable to a reproducible computation, that claim is not verified — fix EDA_FINDINGS.md, not the test.

Then run two checks yourself and record results in ARTIFACT_NOTES.md:

Findings mutation check — in a scratch copy, deliberately change one stated number in EDA_FINDINGS.md to something wrong, rerun the suite, and confirm test_findings_reproduce.py catches it. If it doesn't, that test isn't testing the right thing — strengthen it and repeat until it does, then restore the real file.
Coverage-of-intent check — diff the candidate drivers and flags listed in eda_review.md against what the test suite and EDA_FINDINGS.md actually cover. List anything reviewed but unverified, add a test or a finding for it, and note the addition.
Step 3 — Self-review and resolve
Review the full diff generated so far (loaders, profiling, hypothesis tests, time/leakage checks, notebook, scripts, findings/recommendation/issues docs, tests) as if you were a reviewer seeing it for the first time, with particular attention to: any claim in EDA_FINDINGS.md not actually backed by a reproducible computation, any leakage-tainted variable that made it into MODEL_RECOMMENDATION.md without a caveat, and any hypothesis test using an inappropriate test for the variable's actual shape. For each finding: fix it if it's real, or note in a review log why you're leaving it. Don't leave a list of unresolved findings unaddressed — resolve what you can, and be explicit about what you didn't and why. Write this to review_log.md.
Output Expectations
By the end of a run, the repo should contain:

eda/, scripts/, notebooks/ — generated, analyzing all three heterogeneous sources, with ARTIFACT_NOTES.md.
EDA_FINDINGS.md, MODEL_RECOMMENDATION.md, DATA_ISSUES.md — every numeric claim reproducible via scripts/verify_findings.py, leakage-tainted variables explicitly excluded/caveated in the recommendation.
tests/ (load + profile + hypotheses + time/leakage + findings-reproduce) passing.
notebooks/eda_churn.ipynb runs top to bottom with no manual intervention.
review_log.md documenting the Step 3 self-review and how each finding was resolved.

See the Validation Checklist below for the literal checklist to confirm all of this is in place before handing the build back to the learner.
Guardrails
Do not edit any raw data file (data/customers.csv, data/transactions.db, data/transactions_monthly_agg.parquet). If you find a genuine data defect, note it in ARTIFACT_NOTES.md — never silently patch the source file.
Do not fabricate a p-value, effect size, trend direction, or multi-source gap size in any document. Every number in EDA_FINDINGS.md, MODEL_RECOMMENDATION.md, or DATA_ISSUES.md must come from code that actually ran against the real data, and must be reproducible by scripts/verify_findings.py.
Do not recommend a model family whose reasoning silently relies on a leakage-tainted variable (days since last transaction, trailing-90-day spend, or anything else definitionally derived from the same window as the label) without an explicit caveat.
If an EDA_FINDINGS.md or DATA_ISSUES.md from an earlier phase of this same project is already present when Stage 0 runs, read it and carry its facts and open questions forward — do not regenerate from the raw sources as if no prior phase existed.
Carrying prior context forward is not the same as trusting it blindly: if what you observe directly in the raw data contradicts a specific claim in that prior document, do not silently keep the old claim and do not silently overwrite it either — stop and flag the contradiction explicitly, and let the learner's review resolve it.
Do not fabricate results in ARTIFACT_NOTES.md or review_log.md. If a check genuinely passed cleanly on the first try, say so explicitly rather than inventing a finding — but re-verify the leakage-circularity flag and the multi-source comparison specifically before concluding that.
This assignment involves no secrets, credentials, or API keys — everything runs locally against provided files. Do not introduce any, and do not add a .env requirement that doesn't exist.
This skill implements a confirmed eda_review.md; it does not originate one. If asked to build without a confirmed review present, stop and say so.
Validation Checklist
eda/, scripts/, notebooks/ — generated, analyzing all three heterogeneous sources, with ARTIFACT_NOTES.md
EDA_FINDINGS.md, MODEL_RECOMMENDATION.md, DATA_ISSUES.md — every numeric claim reproducible via scripts/verify_findings.py, leakage-tainted variables explicitly excluded/caveated
tests/ (load + profile + hypotheses + time/leakage + findings-reproduce) passing
notebooks/eda_churn.ipynb runs top to bottom with no manual intervention
review_log.md exists and documents the Step 3 self-review
Discovery note for Claude Code
This file lives at skills/churn-eda-profiling/skill.md inside the assignment package. For Claude Code to auto-discover it as a skill in your own cloned working repo, copy or symlink it into .claude/skills/churn-eda-profiling/skill.md there (mkdir -p .claude/skills/churn-eda-profiling && cp skills/churn-eda-profiling/skill.md .claude/skills/churn-eda-profiling/). If your setup doesn't auto-discover it, paste this file's contents directly as your message when starting the build instead.

