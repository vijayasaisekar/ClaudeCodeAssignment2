# review_log.md — Step 3 self-review

Review of the full build (loaders, profiling, hypothesis tests, time/leakage checks, notebook,
scripts, findings documents, tests) as a reviewer seeing it for the first time.

| # | Finding | Resolution |
|---|---|---|
| 1 | pytest collected the untouched `starter-code/tests/` alongside `tests/`, so imports collided. | Set `testpaths = tests` in pytest.ini. starter-code/ itself was not changed. |
| 2 | The label was implemented as a 90×24h window, which mismatches one customer (697). | Label rule is whole days since last purchase exceeding 90 (matches 1500 of 1500). Diagnostics use whole days. Mismatch logged in DATA_ISSUES.md §2. |
| 3 | Driver tests included customers who signed up inside the label window, who are churned by construction. | Driver population restricted to customers signed up before 2026-05-03 (eligible_customers). DATA_ISSUES.md §3. |
| 4 | Flag reason for days_since_last_txn printed "last inf days". | Unbounded windows described as "all history before as-of". |
| 5 | verify_findings regex missed a unicode minus sign, and one tag was placed before its number, both causing false FAILs. | Replaced with ASCII minus and moved the tag after the number. The verifier then passed all 79 claims. |
| 6 | Test for multi-source mismatch set every July count to 1, which changed nothing. | Test now changes one customer-month, and asserts the diff and the mismatch count. |
| 7 | Notebook executed under the global Python kernel, which lacks matplotlib. | Registered a `churn-eda` kernel pointing at the venv and set it in the notebook metadata. Re-executed with 0 errors. |
| 8 | Multi-source gap undercounted: July has 102 customer-months only in row-level, plus 110 present in both with different counts. | Added the 110 figure as a tagged claim in EDA_FINDINGS.md and DATA_ISSUES.md. |
| 9 | The days-since-last Mann-Whitney p-value is 3.7e-74 exactly, but the notebook's round(v, 4) displays it as 0.0. | Docs state p < 0.0001, which is what the code confirms, and the notebook displays the unrounded value in the probe. |
| 10 | Empty input (TC-005) and a constant driver (TC-004) silently returned NaN or p=1.0. | Added explicit ValueError guards in profile.py and hypotheses.py, with tests. |
| 11 | Stage 0 drafts make claims about amount shape, missingness, leakage and multi-source agreement that are wrong. | Each is corrected with numbers in eda_review.md. Drafts kept unedited in outputs/artifacts/stage0/. |

## Resolved within this build, but worth a human look

- Pre-window drivers fill eligible customers with no pre-window transactions as 0. That is a real zero (no activity before the window), not a missing value, and `derive_pre_window_drivers` documents it.
- The primary recommendation (logistic regression) was not itself fitted here. The assignment excludes building the model; the recommendation rests on the hypothesis results and the data characteristics.

## Left open (not resolved, and why)

- **tenure_days** is in the leakage candidate list and passes the check, but is not hypothesis-tested. It is a static attribute and was left out to keep the driver list short. Add a test if it's to be reported as a driver.
- **Independent reconciliation** of eda_review.md was not performed in a separate conversation. The review was written and checked by the same agent that ran the build.
- **July 2026 in the parquet extract** is incomplete. Its cause (for example a stale extract) can't be established from these files, so the docs state the gap but not its cause.

