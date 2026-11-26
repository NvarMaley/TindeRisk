# RiskMatch V3 — Academic review, 25 November 2026

The single source notebook is [RiskMatch_V3.ipynb](../notebooks/RiskMatch_V3.ipynb).
The executed historical review copy is generated locally in
`data/reports/RiskMatch_V3_professeur.ipynb`. It has 83 executed code cells, no
cell errors, 1,496 rendered checklist entries and full historical responses
from the same server handlers used by the web app. The copy contains local
derived data and requires redistribution-rights review before submission.

## Matching update, 26 November 2026

The table below records the previous engine. The dated replay now refits quarterly,
enforces a one-month execution lag and prices traded securities separately from cash.
HTTP verification produced 35 distinct cards on the standard mandate, five on the
restricted Treasury mandate and one for cash alone. The manual, variance and goal
allocations succeeded in all three cases. The standard paper export reconciled.
The historical notebook replay completed all 83 code cells.

## Chapter-by-chapter cross-check

All 65 representative requests below returned HTTP 200 when the actual
server handler, including JSON serialization, ran in-process. The notebook
also executes a portable numerical fixture for each chapter. The last column
counts the identified chapter tickets within its own checklist section.
Catalog, infrastructure and gate tickets have their own sections.
An experimental result is a successful research calculation with outstanding
validation requirements.
Chapters 14–20 and 23–24 include the core ETF universe and the broader stock
cohort. Ineligible or unavailable strategies appear with their reasons in
the complete response, including unsupported passive-index, managed-futures
and carry implementations.

| Chapter | Replayed result and web location | Formal chapter tickets closed |
|---|---|---:|
| 01 Mandate | Structural preview, dated objectives, funding and constraints; Mandate | 15/15 |
| 02 Behavioral Discovery | Versioned session, answers, score and sensitivity; Risk profile | 16/21 |
| 03 Universe | Dated catalogue and eligibility states; Universe | 11/11 |
| 04 Sources | Source report, coverage and limitations; Research / Sources | 7/9 |
| 05 Point-in-time | Dated snapshot and availability metadata; Research / Sources | 12/12 |
| 06 Returns and FX | Return report and source conventions; Research / Sources | 12/12 |
| 07 Descriptive | Statistics, entire catalogue, SPY and IEF comparison; Universe / asset detail | 9/9 |
| 08 Forecasts | Universe campaign, all asset status records, SPY forecast and historical sentiment; asset detail | 3/11 |
| 09 Volatility | Universe campaign, all asset status records, SPY and aligned covariance; asset detail / compare | 3/10 |
| 10 Factors | Universe campaign, all asset status records, SPY regression; asset detail | 0/11 |
| 11 Tail risk | Universe campaign, all asset status records, SPY and joint tail risk; asset detail / compare | 6/10 |
| 12 Objectives | Mandate projection plus all 11 goal types tested individually; Mandate / Research | 4/10 |
| 13 Baselines | Reference portfolios and dated costs; Research / Reference portfolios | 0/9 |
| 14 Mean–variance | Optimization, weights, diagnostics and frontier; Research / Mean–variance | 9/10 |
| 15 Black–Litterman | Prior, views, posterior and candidate weights; Research / Black–Litterman | 0/9 |
| 16 Hierarchical | Risk parity, HRP, HERC and diversification; Research / Risk parity | 0/11 |
| 17 Downside | Tail and benchmark-relative objectives, frontier; Research / Downside risk | 0/10 |
| 18 Advanced | Robust, resampled, distributionally robust, Kelly, entropy; Research / Advanced optimization | 0/11 |
| 19 Long-only | Strategy signals, portfolios, costs and coverage; Research / Passive and active strategies | 0/10 |
| 20 Alternative | Signed exposure, collateral and experimental strategy status; Research / Alternative strategies | 0/16 |
| 21 Treasuries | Issue coverage, valuations, durations and cash-flow references; Research / Treasuries | 0/12 |
| 22 Futures | Archived ten-family research, rolling/expiry limitations; Research / Futures | 0/11 |
| 23 Walk-forward | Frozen common evaluation, benchmark paths and locked metrics; Research / Backtesting | 0/14 |
| 24 Stress/MC | Stress comparison, five-model selected projection, quantiles, deficits and sensitivity; Research / Stress and Monte Carlo | 0/12 |
| 25 Matching | Personalized construction on the common 575-instrument panel, 48 variants for each of two risk scores and 31 for the constrained Treasury mandate, manual and optimized budgets, joint goal projection; Strategies / My Matches | 0/28 |
| 26 Dynamic | 10 policies plus static and drift, costs, funded ledgers, robustness; My Matches | 0/11 |
| 27 Integration | Reconciled twelve-file paper export, manifest and content hashes; My Matches / Export | 5/15 |

## Asset-level archive integrity

Four current campaigns each contain 1,474 unique catalogue records. Every JSONL
record was parsed, the exact status counts reconciled against its report and
the file SHA-256 matched. The notebook displays all asset statuses and provides
`review.asset_record(campaign, asset_id)` for the complete stored result of
any asset. The batch models have different data requirements.

| Campaign | Computed | Partial or limited analysis | Unavailable |
|---|---:|---:|---:|
| Forecasts | 1,008 | 464 fallback | 2 |
| Volatility and covariance | 574 | 441 partial + 457 descriptive only | 2 |
| Factors | 1,022 | 445 analytical reference | 7 |
| Tail risk | 1,008 | 463 descriptive only | 3 |

The individual asset and aligned SPY/IEF requests are recalculated or retrieved
by the same API adapters as the web application. The archived universe-wide
estimations are checked against their existing data versions and integrity
metadata. Re-estimating every historical fit from raw data is a distinct
reproduction step involving the build scripts and original data entitlements.

## Technical tests and outstanding requirements

- Python unit tests: 178 passed, 5 subtests passed.
- Browser JavaScript tests: 35 passed.
- Notebook: all 83 code cells ran in both portable and local historical
  mode through IPython, with complete saved outputs.
- Three real HTTP integration tests were attempted, but the host environment
  rejected loopback socket binding before the server began listening.
  The in-process handler review still exercises the request and response
  contracts. Visual browser verification and the three socket tests must
  be run on the local host outside that restriction.
- The formal checklist has 222 of 1,230 identified tickets closed, with
  1,008 open. Four are immediately ready under the dependency graph:
  data licensing, dated Treasury ETF holdings verification, a preregistered
  behavioral pilot, and future multi-user authorization. See the
  [consolidation report](CONSOLIDATION.md) and
  [dependency register](TASK_DEPENDENCIES.csv).

## Reproduction

From the project root, install the pinned environment and execute
`.venv/bin/python scripts/execute_notebook.py --historical --save-outputs`.
If kernel ports are restricted, add `--in-process`. The command writes the
historical review copy only under the ignored `data/reports` directory.
The portable source notebook is generated with
`.venv/bin/python scripts/execute_notebook.py --save-outputs`.

This is an academic paper-simulation project. The complete local replay
supports a technical demonstration, subject to the remaining data-rights and
host-browser checks. The checklist and reports explicitly track the independent
validation gates still required for complete methodological acceptance.
