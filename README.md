# Churn EDA & Model-Family Recommendation

Verified exploratory analysis of the churn dataset (three heterogeneous sources: `data/customers.csv`, `data/transactions.db`, `data/transactions_monthly_agg.parquet`), with a model-family recommendation and a data-issues log. No model is trained and no features are built.

## Environment setup

Requires Python 3.10+ (developed on Python 3.14 with pandas 3.1).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate             # macOS / Linux
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install nbclient nbformat ipykernel openpyxl   # used to execute the notebook and edit the rubric
```

No environment variables, API keys or credentials are needed. Everything runs locally against `data/`, and the source files are opened read-only.

## Run the analysis

Run from the repository root, with the venv active. Use `python -m` so `eda/` resolves as a package.

```powershell
python -m scripts.run_profile                     # schema, missingness, zero-activity, amount distribution + outliers
python -m scripts.run_hypothesis_tests            # chi-square / Mann-Whitney tests per candidate driver
python -m scripts.run_time_and_leakage_checks     # monthly trend, row-level vs parquet reaggregation, leakage flags
python -m scripts.verify_findings                 # recomputes every tagged claim in the three findings docs
```

Outputs are written to `outputs/artifacts/`.

### Run the notebook

```powershell
python -m ipykernel install --user --name churn-eda --display-name "Python (churn-eda .venv)"
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/eda_churn.ipynb
```

The notebook's kernel is `churn-eda`, which points at the venv. Opening it in Jupyter with that kernel selected gives the same result. Run it top to bottom in a fresh kernel.

## Run the tests

```powershell
python -m pytest -v
```

`pytest.ini` restricts collection to `tests/`. `tests/test_findings_reproduce.py` checks every stated claim in the findings documents, and includes a mutation test that confirms a wrong number is caught.

## Layout

| Path | Contents |
|---|---|
| `eda/` | `load.py` (loaders), `profile.py` (schema, missingness, distribution, outliers), `hypotheses.py` (one test per driver), `time_checks.py` (trend, multi-source reaggregation), `leakage_checks.py` (label-window circularity, as-of guard) |
| `scripts/` | the four runners above |
| `notebooks/eda_churn.ipynb` | narrative analysis, executed top to bottom |
| `tests/` | 22 tests across loaders, profiling, hypotheses, time/leakage checks, and findings reproduction |
| `eda_review.md` | the corrected review of Stage 0's draft |
| `EDA_FINDINGS.md`, `MODEL_RECOMMENDATION.md`, `DATA_ISSUES.md` | findings; every number is tagged and checked by `verify_findings` |
| `skills/churn-eda-profiling/` | the build spec (`skill.md`, now with its Domain Context section) and its README |
| `outputs/artifacts/` | run outputs, pytest and verify logs, Stage 0 drafts, `ARTIFACT_NOTES.md`, `review_log.md`, plots |

## Key results

- Churn rate 0.1347 overall (202 of 1500); 0.1107 among the 1400 customers who signed up before the label window.
- Zero-activity customers: 81, all churned. They are not missing data.
- `days_since_last_txn` and `trailing_90d_spend` are circular with the label and are excluded.
- Channel and region are null (p ≈ 0.09). Pre-window spend and transaction count are significant but small.
- The monthly parquet extract disagrees with the row-level table for 2026-07 only (237 transactions short).
