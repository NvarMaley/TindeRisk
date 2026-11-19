# ✅ RiskMatch — Project Checklist

> Uses the same numbering as the [README](README.md) and the [`RiskMatch_pipeline.ipynb`](RiskMatch_pipeline.ipynb) notebook.
> Check `[x]` when the task is **completed AND verified**. Enter your initials under “Owner.”
> Legend: 🔴 critical for the grade · 🟡 important · 🟢 bonus
>
> Required order: **data → baselines → simple profile → QARM engines → sentiment → backtest → app → bonus**. A bonus task must not delay a critical task. The completion criteria for each phase are in [`docs/04_EXECUTION_PLAN.md`](docs/04_EXECUTION_PLAN.md).

---

## Step 0 — Organization & Setup

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [x] | 0.1 | Ask the professor the four questions (2026 requirements, StockTwits data, expected backtest, topic approval) | 🔴 | Raf |
| [ ] | 0.2 | Record the presentation date and finalize the schedule | 🔴 | |
| [ ] | 0.3 | Create the GitHub repository and invite all five members | 🔴 | |
| [x] | 0.4 | Create the repository structure (see README) | 🔴 | Codex |
| [ ] | 0.5 | Set up a shared Python environment (initial `requirements.txt`, same Python version) | 🔴 | |
| [x] | 0.6 | `config.yaml`: tickers, dates, SEED, assumptions | 🟡 | Codex |
| [ ] | 0.7 | Complete the six labs (LN1–LN5, LN7) → foundation for the engine | 🔴 | |
| [ ] | 0.8 | Assign roles (README § Team Assignments) | 🔴 | |
| [x] | 0.9 | Freeze the MVP scope and classify HMM/FOMC/adaptive features as extensions | 🔴 | Raf |
| [x] | 0.10 | Start the decision register and experiment log | 🔴 | Codex |
| [ ] | 0.11 | Select and freeze the train/validation/test periods before producing final results | 🔴 | |
| [ ] | 0.12 | Verify licenses and publication rights for data, models, and materials | 🔴 | |
| [ ] | 0.13 | Enable GitHub CI (`pytest` on Python 3.12) | 🔴 | |
| [ ] | 0.14 | Protect `main`: pull request plus review by another member | 🟡 | |
| [ ] | 0.15 | Define “done”: code + test + documentation + reproducible result + review | 🔴 | |
| [ ] | 0.16 | Select the code license and add `LICENSE` before publication | 🟡 | |

## Step 1 — Data Collection

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [x] | 1.1 | Download adjusted prices for the 12 ETFs plus SPY (yfinance, 2005 →) | 🔴 | Raf / Codex |
| [x] | 1.2 | Download DTB3 (FRED) and convert it to a daily rate | 🔴 | Raf / Codex |
| [x] | 1.3 | Download FRED macroeconomic series (T10Y2Y, BAA10Y, VIXCLS, CPIAUCSL, UNRATE, INDPRO) | 🟡 | Raf / Codex |
| [x] | 1.3b | Apply the publication lag to monthly series | 🟡 | Raf / Codex |
| [x] | 1.4 | Obtain the professor's StockTwits data | 🟡 | Vlad |
| [ ] | 1.4b | Build the company → GICS sector mapping table | 🟡 | |
| [x] | 1.5 | Obtain FOMC texts (or the gtfintechlab dataset) with publication dates | 🟢 | 86 dated official statements for January 2010–March 2020. |
| [x] | 1.6 | Clean the data: business-day index, NaNs, duplicates, outliers (market bundle and provisional direct-ETF sentiment) | 🔴 | Raf / Codex |
| [x] | 1.7 | Save to `data/processed/*.parquet` and create `README_data.md` | 🔴 | Raf / Codex |
| [x] | 1.8 | Add `observation_date`, `available_date`, source, and download date — StockTwits retrieval dated 2026-11-17 | 🔴 | Codex / Vlad |
| [x] | 1.9 | Add automated tests for schema, duplicates, gaps, chronology, and coverage (market bundle and provisional direct-ETF sentiment) | 🔴 | Codex |
| [x] | 1.10 | Verify total return/adjusted prices, currency, calendar, and units for each source — [conventions and approximation limits](docs/08_DATA_CONVENTIONS.md) | 🔴 | Codex |
| [x] | 1.11 | Build the common sample for all strategies and document the start of each series — [provisional direct-ETF input and dependencies](docs/09_COMMON_SAMPLE.md) | 🔴 | Codex |
| [x] | 1.12 | Create a small, publishable demonstration dataset with no restricted data — [synthetic offline fixture](data/demo/README.md) | 🔴 | Codex |

<a id="gics-dependency"></a>
### Deferred dependency — historical GICS (1.4b)

By team decision, keep 1.4b open while the historical classification is requested.
This does not block market-data cleaning, equal-weight/GMV/60-40, Classic, ERC,
or a no-views BL baseline. Direct-ETF sentiment is a separate provisional input,
not a replacement for company-sector aggregation.

Return here before completing:

- **4.1c**: dated company-to-sector mapping — historical GICS and identifier links are required.
- **4.1d**: the GICS-based test requires validated 4.1c. The exploratory ICB panel is available in E021.
- **4.3a and 4.6**: company-derived BL views and their out-of-sample validation — require the mapped signal; direct-ETF views must be tested and labelled separately.
- **5.3**: the ERC-anchor implementation is verified. Activating company-sentiment BL requires validated views from 4.6.
- **1.11 and 6.11**: finalize common coverage again when company-derived sentiment is introduced.

The dated Step 1.5 corpus is available for the optional FOMC extension.

### Verified progress — 2026-11-18

- Steps 0.1 and 0.9: professor feedback and approved core/extension scope are recorded in [the decision register](docs/05_DECISIONS.md).
- Steps 1.2, 1.3, 1.3b, and 1.7: [the market-data builder](src/build_market_data.py) generated prices, returns, DTB3, and six macro series locally, with source metadata and checksums. The suite passed 26 tests.
- Step 1.1 verified: all 13 adjusted-close series start on 2005-01-03, with 5,505 observations each through 2026-11-18, including 252 sessions in 2005. Prices are positive and finite, with no missing values or duplicate dates. Raw CSV and processed Parquet values match, and the SHA-256 checksum is verified. The shared configuration now starts on 2005-01-01; the market bundle was regenerated consistently. All 26 tests pass. The final session may still be provisional until the US market closes; this is not a frozen final backtest dataset.
- Step 1.4: Vlad's published firm-day StockTwits artifact is present. [The asset-sentiment builder](src/build_sentiment_assets.py) generated 43,438 direct-ETF/SPY observations covering all 13 assets.
- Step 1.4b remains open: direct ETF tags are a provisional input, not a validated historical company-to-GICS mapping.
- Step 1.4b source audit: the local CRSP monthly extract contains `Ticker`, `PERMNO`, `SICCD`, `NAICS`, `ICBIndustry`, and security-history dates; the Compustat annual extract contains `gvkey`, `datadate`, and `sich`. Neither extract contains historical GICS sector codes. Completion requires a dated GICS classification linked to stable company identifiers, plus historical ticker validity and classification availability dates. SIC/ICB codes and today's classifications must not be silently substituted for historical GICS. This source dependency remains unresolved; the direct-ETF signal is still provisional.
- Step 1.6 passed for the market bundle and provisional direct-ETF sentiment: `python -m src.audit_data` checked all 5,505 price sessions for 13 assets against the NYSE calendar, with zero missing/unexpected sessions, complete positive finite prices, consistent returns, and aligned risk-free/excess returns. No absolute daily moves exceeded the 25% review threshold. Sentiment availability now uses the strictly next NYSE session, tested on holidays, weekends and the 2012 Hurricane Sandy closure; the asset artifact was regenerated. Zero-labelled days retain undefined polarity rather than being replaced by artificial zeros. The local market report is `data/processed/quality_report.json`; 30 tests pass. Re-run these checks when company-derived sentiment is introduced after [1.4b](#gics-dependency).
- Step 1.8 records the reported StockTwits retrieval date, Tuesday 17 November 2026, on all 43,438 direct-ETF/SPY provenance rows. Common market samples are prepared in 1.11; final train/validation/test periods and signal eligibility remain open in 0.11 and 4.3c/4.6. Monthly FRED lags do not eliminate revision bias in latest-vintage data.
- Step 1.8 implemented and generated: market and direct-ETF sentiment provenance sidecars retain observation and modelled availability dates, source, retrieval status, actual Yahoo/FRED retrieval timestamps, and source checksums. The sentiment sidecar and metadata record the calendar date in `download_date`. The reported approximate time is noon in Europe/Zurich. The exact UTC timestamp remains null. Details and remaining timing limitations: [data provenance](data/README_data.md#observation-level-provenance-step-18). Before final backtesting, review same-date DTB3 usage and distinguish latest-vintage FRED assumptions from genuine point-in-time information. Work on 1.9 can proceed independently of this provider dependency.
- Step 1.9 verified: 52 tests pass, including deliberately invalid schemas, duplicate/unsorted dates, missing NYSE sessions, holiday availability, nonfinite/fractional counts, inconsistent polarities, corrupted return arithmetic, misaligned risk-free/macro inputs and missing configured assets. `python -m src.audit_data` passes on the local bundle and checks stored SHA-256 hashes. The report measures sentiment coverage and undefined polarity per asset, without filling observations. IEF has 950 NYSE sessions without a message-date observation between its first/last observations; these are not assumed to be neutral sentiment or lost source rows. Revisit coverage and signal eligibility in **1.11, 4.3c and 4.6**. Passing quality tests is not proof of predictive power or point-in-time source validity; the [GICS gate](#gics-dependency) remains open.
- Step 1.10 verified: `python -m src.check_conventions` confirmed USD quote currency and New York exchange timezone for all 13 tickers, cross-checked adjusted returns against Yahoo Adj Close over 2019, and verified DTB3 percent-to-decimal daily-proxy arithmetic. Macro units, transforms, return annualization and StockTwits units are documented with official source links in [data conventions](docs/08_DATA_CONVENTIONS.md). The local timestamped report is `data/processed/conventions_report.json`; 56 tests pass. DTB3/100/252 remains an explicitly approximate proxy, not an exact bill holding-period return. Resolve publication timing and cash/borrowing accrual in 6.1/6.3; this completed convention audit is not certification of historical vintages or predictive signals.
- Step 2 work implemented by Raf is present in the notebook. Step 2.1 has now been reproduced; later Step 2 boxes remain open pending their own verification.

Step 1.11 verified: [common-sample builder](src/build_common_sample.py) generated
2,578 common main sessions (2010-01-04–2020-03-31) and 4,497 extended sessions
(2009-01-02–2026-11-17), excluding the unfinished current session. Both preserve
756 strictly prior warm-up returns. Sentiment counts are grouped by availability
session; missing views stay missing and do not remove market dates. Input/output
hashes, per-series starts and signal coverage are saved locally. 60 tests pass.
See [the sample specification](docs/09_COMMON_SAMPLE.md) before 4.3c/4.6, 5.3,
and 6.1/6.11. Rebuild after the [GICS dependency](#gics-dependency) is resolved;
this does not close the final holdout or predictive-validation tasks.

## Step 2 — Exploration & Estimation

Step 1.12 verified: [the demo generator](src/demo_data.py) creates a fixed-seed,
fully synthetic fixture committed under [data/demo](data/demo/README.md), about
160 KB. It contains no source observations, uses explicit synthetic labels,
and loads offline through `load_demo()` without writing to production paths.
Market and sentiment schema/arithmetic audits pass, including intentional
missing observations and undefined polarity. 63 tests pass. This completes the
data fixture only: app demo integration, visible labelling and missing-artifact
messages remain in **8.8/8.12**; no performance claim or production warm-up is
supported by the short fixture. GICS (1.4b) and FOMC (1.5) remain open.
Market-only Step 2 work can proceed.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [x] | 2.1 | Compute descriptive statistics by asset (return, volatility, Sharpe, skewness, kurtosis, max drawdown) — [reproduction and definitions](docs/10_DESCRIPTIVE_STATISTICS.md) | 🟡 | Raf / Codex |
| [x] | 2.1b | Create a correlation heatmap and rolling equity/bond correlation — implemented and locally verified | 🟡 | Raf / Codex |
| [x] | 2.2 | Three-year rolling Σ: sample vs. Ledoit-Wolf — implemented and locally verified | 🔴 | Raf / Codex |
| [ ] | 2.2b | Demonstrate instability (composition maps, LN3 lab) | 🟢 | |
| [x] | 2.3 | Select, implement, and document a conservative μ estimator — regularized Bayes–Stein-style mean; [definitions and limits](docs/13_EXPECTED_RETURNS.md) | 🔴 | Raf / Codex |
| [x] | 2.4 | Set the reference Sharpe ratio SR_T and perform sensitivity analysis — [0.35 and 40 scenarios](docs/14_REFERENCE_SHARPE.md) | 🔴 | Raf / Codex |
| [x] | 2.5 | Implement reproducible baselines: equal-weighted, GMV, and 60/40 — [monthly results and assumptions](docs/15_BASELINES.md) | 🔴 | Codex |
| [x] | 2.6 | Run diagnostics for normality, autocorrelation, historical ES, and subperiod stability — [112 verified rows](docs/16_SUBPERIOD_DIAGNOSTICS.md) | 🟡 | Codex |
| [x] | 2.7 | Add unit-consistency tests: daily/annual, variance/volatility, simple/log/excess return — [offline audit and formulas](docs/17_RETURN_UNITS.md) | 🔴 | Codex |
| [x] | 2.8 | Compare sample/LW by conditioning, weights, turnover, and realized-volatility error — [method and results](docs/18_COVARIANCE_COMPARISON.md) | 🔴 | Codex |
| [ ] | 2.9 | LN3 option: use the resampled frontier as a demonstration, not a production requirement | 🟢 | |

Step 2.1 verified: [shared statistics](src/descriptive.py) and
[the reproducible builder](src/build_descriptive.py) regenerate 14-row tables
(13 assets plus a daily-rebalanced descriptive 60/40 reference) for the main
and extended common samples. Eleven original metric columns match Raf's old
notebook formulas on identical inputs to numerical tolerance. Drawdown now
includes initial wealth so first-day losses are counted. 67 tests pass,
including hand-checkable drawdown, CAGR, volatility, Sharpe and tail-return
cases, constant-series handling and invalid inputs. Local CSVs and an
input/output-hashed manifest are saved under results; the notebook source
uses the shared main-sample implementation and labels saved old outputs
as stale. This does not close 2.6, create a monthly baseline, or validate a
strategy. See [the diagnostic specification](docs/10_DESCRIPTIVE_STATISTICS.md).

## Step 3 — Client Profile: Baseline, Then Adaptive Questionnaire

> The **fixed, transparent profile** takes priority. The adaptive engine remains a bonus until its real-world validity and stability have been demonstrated.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [x] | 3.0a | Define capacity, tolerance, knowledge, objectives, and constraints separately — [fixed profile specification](docs/19_PROFILE_DIMENSIONS.md) | 🔴 | Codex |
| [x] | 3.0b | Draft the fixed 10–15-question baseline using neutral wording — [14 questions](questions/fixed_mvp.json) | 🔴 | Codex |
| [x] | 3.0c | Define fully explainable scoring rules and capacity caps — [tables and examples](docs/20_FIXED_PROFILE_SCORING.md) | 🔴 | Codex |
| [x] | 3.0d | Freeze and document the JSON `profile` output format — [v1 schema and example](docs/21_PROFILE_JSON.md) | 🔴 | Codex |
| [ ] | 3.0e | Conduct user testing for comprehension, edge cases, and test-retest stability — [protocol ready and synthetic cases verified](docs/22_PROFILE_PILOT.md); participant sessions pending | 🔴 | Codex |
| [x] | 3.0f | Display that the tool is academic and not psychometrically certified — Profile page, rendering checked in notebook | 🔴 | Codex |
| [x] | 3.0g | Test profile serialization, import/export, and version compatibility — [v1 round trip and compatibility rules](docs/21_PROFILE_JSON.md#step-30g--file-round-trip) | 🔴 | Codex |
| [x] | 3.1a | Draft the 10 Block A questions (capacity) — [cards and research references](questions/README.md#adaptive-cards--step-31a) | 🟢 | Codex |
| [x] | 3.1b | Draft the 20 Block B questions (tolerance, ordered scales) — [card design](questions/README.md#tolerance-cards--step-31b) | 🟢 | Codex |
| [x] | 3.1c | Generate the 24 Block C pairs with φ_seuil on a log grid [0.5, 20] — [card design](questions/README.md#paired-swipe-cards--step-31c) | 🟢 | Codex |
| [x] | 3.1d | Draft the six Block D questions (constraints) plus branching conditions — [verified routes](questions/README.md#constraint-cards--step-31d) | 🟢 | Codex |
| [x] | 3.1e | Store the question bank in `questions/bank.json` (README format) | 🟢 | Codex |
| [x] | 3.2a | Implement swipe likelihood (logit on ΔU, parameter λ) | 🟢 | Codex |
| [x] | 3.2b | Implement scale likelihood (graded response / ordered logit) | 🟢 | Codex |
| [x] | 3.2c | Set prior parameters for Block B items (a, b_k) | 🟢 | Codex |
| [x] | 3.3 | Implement the grid-based Bayesian engine (prior, update, mean/median, SD, 80% CI) | 🟢 | Codex |
| [x] | 3.4 | Implement adaptive selection (minimize expected posterior variance) plus block quotas | 🟢 | Codex |
| [x] | 3.5 | Define the stopping rule (SD < threshold or 15 questions) | 🟢 | Codex |
| [x] | 3.6 | Add a mirrored question, inconsistency detection, and messages | 🟢 | Codex |
| [x] | 3.7 | Define capacity rules → σ*_cap (maximum loss, horizon, liquidity) — [calculation and limiting answers](docs/20_FIXED_PROFILE_SCORING.md) | 🔴 | Codex |
| [x] | 3.8 | Calibrate Tobin φ → σ*_tol, apply the capacity cap, then recalculate achieved volatility | 🔴 | Codex |
| [x] | 3.8b | Map the capped continuous estimate deterministically to Conservative, Balanced, Growth, or Aggressive | 🔴 | Codex |
| [x] | 3.8c | Test every category boundary and verify that capacity always overrides higher tolerance | 🔴 | Codex |
| [x] | 3.8d | Show category, range, and plain-language explanation to clients; keep φ and precise σ values in technical details | 🔴 | Codex |
| [x] | 3.9a | Build a synthetic-client simulator (1,000 φ values, noisy responses) | 🟢 | Codex |
| [x] | 3.9b | Compare adaptive vs. random vs. fixed vs. 60 questions (RMSE, σ* error, % correctly classified) | 🟢 | Codex |
| [x] | 3.9c | Plot “error vs. number of questions” (pitch figure) | 🟢 | Codex |
| [x] | 3.9d | Test robustness to high noise and misspecified parameters | 🟢 | Codex |
| [ ] | 3.10 | (Optional) Conduct a real survey of 40–60 students, recalibrate, and prune items — protocol ready; data pending | 🟢 | Codex |
| [ ] | 3.11 | Compare adaptive and fixed profiles with real participants — protocol ready; data pending | 🟢 | Codex |

[Chapter 3 implementation, simulation and study protocol](docs/23_ADAPTIVE_PROFILE.md).

## Step 4 — Signals

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 4.1 | Reproduce LN7: market/company polarity, abnormal volume, events, AR/AP/CAR/CAP | 🔴 | Both Moodle files verified. Supplied labels total 1,131 events. The independent reconstruction finds 1,414, with 993 supplied ticker/date/type matches. |
| [x] | 4.1b | Reproduce at least one expected LN7 lab result before making any adaptations | 🔴 | SPY daily returns, 5/5 at six decimals, 4–8 Jan 2010. |
| [ ] | 4.1c | Build a dated and validated company → sector mapping — [requires 1.4b](#gics-dependency) | 🔴 | Dated identifiers match 37,955 / 42,154 observed ticker-days. Historical GICS export pending. |
| [ ] | 4.1d | Test sector aggregation as a distinct hypothesis — [requires mapped companies](#gics-dependency) | 🟡 | Exploratory ICB panel E021: 89.8% coverage and 622 defined industry-months. GICS-based return test awaits 4.1c. |
| [ ] | 4.1e | Test Mann-Whitney/robust regression and out-of-sample stability | 🔴 | Exploratory direct-ETF and reconstructed event rank tests run. Exact event replication and company-derived sector tests remain open. |
| [ ] | 4.2 | Run offline FOMC classification → tone index per document | 🟢 | Baseline scored 86 releases. The specified FOMC-RoBERTa checkpoint requires authorized access. |
| [ ] | 4.3a | Define relative sentiment views `P`; include the Fed only if the extension is validated — [GICS dependency for company-derived views](#gics-dependency) | 🔴 | Matrix implemented and verified. Zero eligible views while signal validation is pending. |
| [ ] | 4.3b | Estimate `Q` on train/validation data only; disable the view if unstable | 🔴 | Estimator tested. Live calibration awaits an approved view and the frozen final-test boundary. |
| [ ] | 4.3c | Base `Omega` on genuinely available confidence, with sensitivity analysis | 🔴 | Validation-error method and sensitivity verified on synthetic data. Historical calibration awaits an active view. |
| [x] | 4.4a | Fit an HMM to standardized macroeconomic variables (select the number of states using BIC) | 🟢 | Four states selected on the 2005–2015 exploratory sample. Recheck with historical FRED vintages before backtesting. |
| [x] | 4.4b | Use expanding-window estimation and **filtered** probabilities | 🟢 | 24 exploratory monthly estimates; future-input invariance verified. Rebuild with historical vintages for backtesting. |
| [x] | 4.4c | Name and describe the regimes | 🟢 | Four exploratory profiles documented and visualized on the 2005–2015 fit. |
| [x] | 4.5 | Freeze the signal definition before the test period and maintain the experiment log | 🔴 | [Protocol v1](docs/24_SIGNAL_PROTOCOL.md) and [experiment log](docs/06_EXPERIMENT_LOG.md) recorded. Final-test split remains open in 0.11. |
| [ ] | 4.6 | Validate StockTwits out of sample before producing BL views — [distinguish company and direct-ETF signals](#gics-dependency) | 🔴 | Direct-ETF spread reversed in exploratory validation. Company test E014 awaits dated GICS and the fixed split. |
| [x] | 4.7 | Compare the HMM with a static/GMM baseline; use filtered probabilities only | 🟢 | HMM wins on 21/24 exploratory macro months; average log-score advantage +0.686 nats. |
| [x] | 4.8 | Reproduce LN7 abnormal returns using a market model; do not replace it with a moving average | 🔴 | Original Moodle inputs: 5/5 displayed AAPL rows at six decimals and 37,950/37,950 supplied residuals within numerical tolerance. |
| [x] | 4.9 | Decide how to handle the post-2020 period: historical demonstration or a new validated source | 🔴 | Historical-only, with a 31 March 2020 cutoff and no later StockTwits views. [DR-06](docs/05_DECISIONS.md#dr-06--stocktwits-coverage). |
| [ ] | 4.10 | Compare all strategies on a common sample, then report longer histories separately | 🔴 | Calendar control verified. Full performance comparison awaits Step 5 strategy returns and Step 6 backtests. |

[LN7 replication inputs](data/README_data.md#ln7-lab-reproduction) and
[historical company-link audit](data/README_data.md#ln7-historical-company-to-sector-links).
[Sector sentiment hypothesis](data/README_data.md#company-derived-sector-sentiment)
and [statistical checks](data/README_data.md#stocktwits-statistical-checks).

## Step 5 — Portfolio Construction

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [x] | 5.0 | Implement and test shared functions (`vol`, `risk_contrib`, `tracking_error`, `erc`, `risk_budget`, `bl_posterior`, `target_vol`) | 🔴 | Euler, risk budgets, BL and cash scaling verified. Notebook check: 12 ETFs, ERC risk-share error below 2e-11. |
| [x] | 5.1 | 🏛️ Classic: constrained long-only tangency portfolio (LW Σ, conservative μ) | 🔴 | 96 month-end fits satisfy all caps. Notebook checks against capped GMV using the same estimates. |
| [x] | 5.2 | ⚖️ Balanced: ERC (log barrier + rescaling) | 🔴 | 96 month-end fits verified. The raw sleeve exceeds the 35% cap on 11 dates. Apply client constraints in 5.6b. |
| [x] | 5.3 | 🧠 Connected: BL (`x0`, implied and posterior means, target TE) — [company-view prerequisite](#gics-dependency) | 🔴 | 214 month-end fits match ERC exactly. Synthetic view reaches 3% TE. Real views remain gated by 4.6. |
| [x] | 5.4 | 🌦️ Chameleon: regime budgets weighted by filtered probabilities | 🟢 | 24 exploratory fits meet their risk budgets. Historical vintages and changing regimes are needed to assess portfolio utility. |
| [x] | 5.5 | 📈 60/40 benchmark | 🔴 | Verified monthly SPY/IEF drift and gross daily returns on 2,578 main and 4,498 extended sessions. |
| [x] | 5.6a | Apply Tobin scaling toward each risk band's reference volatility (plus leverage rule) | 🔴 | 3,072 allocations checked. Default 1×. Explicit leverage variant uses 1.5× and reports achieved volatility and shortfalls. |
| [x] | 5.6b | Re-optimize under client constraints (exclusions, maximum weights) | 🔴 | 144 allocations checked for exclusions, ETF caps, borrowing permission and effective risk targets. |
| [x] | 5.6c | Build the versioned `risk_band × strategy` prepared portfolio catalogue | 🔴 | 16 dated allocations in `portfolio_catalogue.parquet`. Out-of-range allocations flagged. Historical metrics await Step 6. |
| [x] | 5.7 | Produce analytics: weights, RC/RC*, volatility, TE, IR, concentration | 🔴 | Risk analytics saved in catalogue v2. IR calculation tested; realized ratios await matched Step 6 returns. |
| [x] | 5.8 | Select and document the BL reference portfolio (`x0`) | 🔴 | DR-02 selects ERC. Implied Sharpe and recovery with an independent tangency solve verified on 96 month-ends. |
| [ ] | 5.9 | Analyze BL sensitivity to `x0`, `tau`, and `Omega`, with/without views | 🔴 | |
| [ ] | 5.10 | Produce LN6 analytics: Expected Shortfall, Herfindahl, Shannon, diversification ratio | 🟡 | |
| [ ] | 5.11 | Recalculate and display the volatility actually achieved after constraints/leverage | 🔴 | |
| [ ] | 5.12 | Test constraints: weights sum to 1, bounds, classes, exclusions, explicit solver failure | 🔴 | |
| [ ] | 5.13 | Verify that BL without views reproduces the prior and that a higher-confidence view produces a stronger tilt | 🔴 | |
| [ ] | 5.14 | Add a turnover constraint/penalty if justified by the net benefit | 🟡 | |

## Step 6 — Backtest

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 6.1 | Build a monthly backtest engine (weight drift, cash at DTB3) — first resolve [cash timing/accrual conventions](docs/08_DATA_CONVENTIONS.md#risk-free-proxy-explicit-approximation) | 🔴 | |
| [ ] | 6.2 | Run the four risk-band reference targets × active MVP strategies | 🔴 | |
| [ ] | 6.3 | Model transaction costs and two-way turnover (0 / 10 / 25 bps) — verify [rate units and financing conventions](docs/08_DATA_CONVENTIONS.md#risk-free-proxy-explicit-approximation) | 🔴 | |
| [ ] | 6.4 | Compute metrics (including **realized volatility vs. σ\***) and performance by regime | 🔴 | |
| [ ] | 6.5 | Test robustness to window, frequency, subperiods, and shrinkage | 🟡 | |
| [ ] | 6.6 | Export `results/*.parquet` | 🔴 | |
| [ ] | 6.7 | Add an anti-look-ahead test: weights at `t` use no subsequent returns | 🔴 | |
| [ ] | 6.8 | Report gross and net results, plus alpha/beta with HAC errors | 🟡 | Use the local `data_plus/clean/daily_factors.parquet` Fama–French series for a factor diagnostic on overlapping dates. |
| [ ] | 6.9 | Preserve a frozen final test; distinguish confirmatory from exploratory analyses | 🔴 | |
| [ ] | 6.10 | Verify the weight lag: decision at `t`, return earned at `t+1` | 🔴 | |
| [ ] | 6.11 | Compare over a common period; present longer histories separately | 🔴 | |
| [ ] | 6.12 | Save weights, trades, costs, diagnostics, and the configuration version for every run | 🔴 | |
| [ ] | 6.13 | Run the pipeline twice with the same seed and obtain identical results | 🔴 | |
| [ ] | 6.14 | Export a common-period, net-of-cost summary for every category-strategy pair | 🔴 | |
| [ ] | 6.15 | Export the five client metrics: historical net return, realized volatility, net Sharpe, maximum drawdown, annualized cost | 🔴 | |
| [ ] | 6.16 | Export technical metrics: Sortino, Calmar, ES, turnover, concentration, TE, IR, and risk contributions | 🟡 | |
| [ ] | 6.17 | Generate prespecified, evidence-backed advantages and limitations; never rank by return alone | 🔴 | |

## Step 7 — Selection & Monitoring

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 7.1 | Record the selection (profile, risk band, strategy, catalogue version, shown metrics, date, initial prices, weights, amount) | 🔴 | |
| [ ] | 7.2 | Run Monte Carlo simulations (normal + block bootstrap) and calculate the probability of reaching the objective | 🟢 | |
| [ ] | 7.3 | Include historical monitoring in the MVP; enable live mode only with reliable current data | 🟡 | |
| [ ] | 7.4 | Define rebalancing rules (calendar / threshold) and alerts | 🟡 | |
| [ ] | 7.5 | Implement brief re-profiling (five questions, prior = previous posterior) | 🟢 | |
| [ ] | 7.6 | Create a downloadable client report | 🟢 | |
| [ ] | 7.7 | Add persistence through JSON export/import | 🟡 | |
| [ ] | 7.8 | Keep frozen historical evidence separate from live performance since selection | 🔴 | |
| [ ] | 7.9 | Update value, benchmark, drawdown, weight drift, rolling risk, and alerts from latest daily prices | 🟡 | |

## Step 8 — Web App

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 8.1 | Build a multipage skeleton (Home + four pages), **deployed by week 2** | 🔴 | |
| [ ] | 8.2 | Implement `st.session_state` (responses, profile, selection; posterior only if adaptive) | 🔴 | |
| [ ] | 8.3a | Build the Profile page (one question at a time, then category, range, capacity explanation, constraints) | 🔴 | |
| [ ] | 8.3b | Build the Portfolios page (same-band cards, five primary metrics, pros/cons, common-period label) | 🔴 | |
| [ ] | 8.3c | Build the optional Analysis page (weights, RC, Sortino, Calmar, ES, turnover, concentration, technical backtest) | 🔴 | |
| [ ] | 8.3d | Build the Monitoring page (since-selection value, benchmark, drawdown, drift, risk-band status, alerts, export) | 🟡 | |
| [ ] | 8.4 | Add caching and perform no heavy computation online | 🔴 | |
| [ ] | 8.5 | Create the design (palette, characters, “technical details” mode) | 🟡 | |
| [ ] | 8.6a | Add `pytest` unit tests (Euler, ERC, BL without views, posterior, Tobin) | 🔴 | |
| [ ] | 8.6b | Run an end-to-end test with 20 simulated profiles and no errors | 🔴 | |
| [ ] | 8.7 | Deploy to Streamlit Cloud, test on a phone, and provide a public link | 🔴 | |
| [ ] | 8.8 | Provide a local demonstration dataset and clear messages when an artifact is missing | 🔴 | |
| [ ] | 8.9 | Display the result date, assumptions, limitations, and academic disclaimer | 🔴 | |
| [ ] | 8.10 | Test installation on a clean computer | 🔴 | |
| [ ] | 8.11 | Never download data or recompute a heavy backtest during an interaction | 🔴 | |
| [ ] | 8.12 | Hide/label every feature whose artifact has not been validated | 🔴 | |
| [ ] | 8.13 | Test keyboard navigation, contrast, mobile display, and error messages | 🟡 | |
| [ ] | 8.14 | Label every historical result as non-forecast and never call a strategy “best” | 🔴 | |
| [ ] | 8.15 | User-test whether non-technical users understand the category and five card metrics | 🔴 | |

## Step 9 — Pitch

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 9.1 | Prepare a 15-minute storyline (problem → demonstration → under the hood → limitations → Q&A) | 🔴 | |
| [ ] | 9.2 | Rehearse the demonstration with the fictional professor-client (prepared response scenario + backup plan for network failure) | 🔴 | |
| [ ] | 9.3 | Prepare a list of challenging questions and answers | 🔴 | |
| [ ] | 9.4 | Complete two timed rehearsals | 🔴 | |
| [ ] | 9.5 | Verify the final GitHub README and the app link in the README | 🔴 | |
| [ ] | 9.6 | Prepare an offline demonstration (screenshots/video/preloaded results) | 🔴 | |
| [ ] | 9.7 | Verify that every claim in the pitch points to a reproducible result | 🔴 | |

## Step 10 — Final Audit & Release

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 10.1 | Run the full test suite in CI and locally | 🔴 | |
| [ ] | 10.2 | Reproduce the results from a fresh clone of the repository | 🔴 | |
| [ ] | 10.3 | Verify that no secrets, restricted data, or course materials are versioned | 🔴 | |
| [ ] | 10.4 | Verify README links, license, versions, and launch instructions | 🔴 | |
| [ ] | 10.5 | Freeze a presentation release/tag and archive the artifacts used | 🔴 | |
| [ ] | 10.6 | Conduct a cross-audit: each component reviewed by a member who did not develop it | 🔴 | |
| [ ] | 10.7 | Complete the full app journey and pitch with the network disconnected | 🔴 | |

---

### Open Decisions (to Be Resolved as a Group)

- [x] Black-Litterman reference portfolio (`x0`): ERC, approved 2026-11-17 (DR-02); 60/40 for sensitivity
- [x] Leverage permitted up to 1.5×, borrowing spread 100 bps, approved 2026-11-17 (DR-03)
- [ ] Final list of macroeconomic variables and number of regimes
- [x] Reference SR_T value for profiling — 0.35 with documented sensitivity
- [ ] Volatility caps by horizon (capacity rules)
- [ ] Risk budgets by regime (Chameleon)
- [ ] CHF option (currency risk): yes / no
- [ ] Conduct the real survey (3.10): yes / no
- [ ] Final test start date and common StockTwits period
- [ ] Code license and publishable demonstration files

### Steps 2.1b / 2.2 — local verification, 2026-11-18

[The reproducible builder](src/build_dependence.py) exports main/extended
correlations, six inspected figures and covariance estimates over 756 trailing
sessions at completed NYSE month-end closes (123 main / 214 extended dates).
Sample, constant-correlation LW (LN3) and scaled-identity LW are distinguished.
The constant-correlation moment normalization and equal-target edge case have
been corrected. Hash, formula, chronology and integration checks pass;
`make check` passes 85 tests. [Definitions and evidence](docs/12_CORRELATION_COVARIANCE.md).
Rows checked at the user’s explicit request after local verification; independent peer review remains pending in PR #2. This does not complete
2.2b, 2.5 or 2.8, and does not certify the old notebook outputs or a backtest.

### Step 2.3 — verified implementation, 2026-11-18

[The expected-return builder](src/build_expected_returns.py) exports Raf's
regularized Bayes–Stein-style excess-mean shrinkage default on the main and
extended common calendars (123 / 214 month-end estimates, 756 trailing sessions).
Daily LW asset covariance, daily excess-mean inputs and final annualization
are explicit; the raw mean is a control only. All 337 estimates were checked
against an independent inverse-form calculation, both figures inspected and
output hashes verified. `make check` passes 96 tests, including 11 new tests.
[DR-05 and definitions](docs/13_EXPECTED_RETURNS.md) distinguish this variant
from exact Jorion optimality, an investable GMV and the BL ERC anchor.
No future-return ranking, predictive superiority or final OOS certification
is claimed; 0.11, DTB3 timing/accrual, 2.4 and optimization remain open.
