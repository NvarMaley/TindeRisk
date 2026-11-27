# RiskMatch V3 — Academic review, 27 November 2026

The single source notebook is [RiskMatch_V3.ipynb](../notebooks/RiskMatch_V3.ipynb).
The executed historical review copy is generated locally in
`data/reports/RiskMatch_V3_professeur.ipynb`. It has 83 executed code cells, no
cell errors, 1,496 rendered checklist entries and full historical responses
from the same server handlers used by the web app. The copy contains local
derived data and requires redistribution-rights review before submission.

## Client implementation, 27 November 2026

The active mandate shows ten goals. Discovery uses 30 fixed cards, with 20
feeding the prudence index and eight supporting experimental loss-aversion
ranges. The portfolio engine uses `1 + 13.3 q²` for mean–variance calibration.
The client Universe and personalized construction use the same dated universe of US stocks, equity ETFs, US Treasury ETFs
and a USD cash proxy. Listed instruments need 60 consecutive monthly total
returns through 31 December 2025. At the cutoff the client catalogue has 642 US stocks, 15 equity ETFs, five Treasury ETFs and one cash allocation. Chapters 8–24 also retain separate archived experiments with their own cohorts. See the [client flow](CLIENT_FLOW.md) and
[personalized methodology](PERSONALIZED_MATCHING.md).

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

| Chapter | Replayed result and location | Formal chapter tickets closed |
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
| 12 Objectives | Mandate projection plus all 11 goal types tested individually; notebook and mandate | 4/10 |
| 13 Baselines | Reference portfolios and dated costs; notebook | 0/9 |
| 14 Mean–variance | Optimization, weights, diagnostics and frontier; notebook | 9/10 |
| 15 Black–Litterman | Prior, views, posterior and candidate weights; notebook | 0/9 |
| 16 Hierarchical | Risk parity, HRP, HERC and diversification; notebook | 0/11 |
| 17 Downside | Tail and benchmark-relative objectives, frontier; notebook | 0/10 |
| 18 Advanced | Robust, resampled, distributionally robust, Kelly, entropy; notebook | 0/11 |
| 19 Long-only | Strategy signals, portfolios, costs and coverage; notebook | 0/10 |
| 20 Alternative | Signed exposure, collateral and experimental strategy status; notebook | 0/16 |
| 21 Treasuries | Issue coverage, valuations, durations and cash-flow references; notebook | 0/12 |
| 22 Futures | Archived ten-family research, rolling/expiry limitations; notebook | 0/11 |
| 23 Walk-forward | Frozen common evaluation, benchmark paths and locked metrics; notebook | 0/14 |
| 24 Stress/MC | Stress comparison, five-model selected projection, quantiles, deficits and sensitivity; notebook | 0/12 |
| 25 Matching | Personalized construction on the 60-month portfolio panel, the compatible methods, a featured shortlist, a common-period comparison and a restricted Treasury example, manual and optimized budgets, joint goal projection; Strategies / My Matches | 0/28 |
| 26 Dynamic | 10 policies plus static and drift, costs, funded ledgers, robustness; My Matches | 0/11 |
| 27 Integration | Reconciled twelve-file paper export, manifest and content hashes; My Matches / Export | 5/15 |

## Asset-level archive integrity

Four archived research campaigns each contain 1,474 unique catalogue records. Every JSONL
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

- Python unit tests: 199 passed, 5 subtests passed.
- Browser JavaScript tests: 40 passed.
- Notebook: all 83 code cells ran in both portable and local historical
  mode through IPython, with complete saved outputs.
- Local HTTP integration and Chromium acceptance checks passed. The client
  flow covered the 30 Discovery cards, strategy generation, allocation,
  confirmation and the objectives report. Position tracking reports when an
  external quote feed is unavailable.
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
supports a local technical demonstration. Remote access requires a working
link to this version and an authorized host with the local archive. The checklist and reports explicitly track the independent
validation gates still required for complete methodological acceptance.
