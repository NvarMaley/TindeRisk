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
| [ ] | 0.1 | Ask the professor the four questions (2026 requirements, StockTwits data, expected backtest, topic approval) | 🔴 | |
| [ ] | 0.2 | Record the presentation date and finalize the schedule | 🔴 | |
| [ ] | 0.3 | Create the GitHub repository and invite all five members | 🔴 | |
| [x] | 0.4 | Create the repository structure (see README) | 🔴 | Codex |
| [ ] | 0.5 | Set up a shared Python environment (initial `requirements.txt`, same Python version) | 🔴 | |
| [x] | 0.6 | `config.yaml`: tickers, dates, SEED, assumptions | 🟡 | Codex |
| [ ] | 0.7 | Complete the six labs (LN1–LN5, LN7) → foundation for the engine | 🔴 | |
| [ ] | 0.8 | Assign roles (README § Team Assignments) | 🔴 | |
| [ ] | 0.9 | Freeze the MVP scope and classify HMM/FOMC/adaptive features as extensions | 🔴 | |
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
| [ ] | 1.1 | Download adjusted prices for the 12 ETFs plus SPY (yfinance, 2005 →) | 🔴 | |
| [ ] | 1.2 | Download DTB3 (FRED) and convert it to a daily rate | 🔴 | |
| [ ] | 1.3 | Download FRED macroeconomic series (T10Y2Y, BAA10Y, VIXCLS, CPIAUCSL, UNRATE, INDPRO) | 🟡 | |
| [ ] | 1.3b | Apply the publication lag to monthly series | 🟡 | |
| [ ] | 1.4 | Obtain the professor's StockTwits data | 🟡 | |
| [ ] | 1.4b | Build the company → GICS sector mapping table | 🟡 | |
| [ ] | 1.5 | Obtain FOMC texts (or the gtfintechlab dataset) with publication dates | 🟢 | |
| [ ] | 1.6 | Clean the data: business-day index, NaNs, duplicates, outliers | 🔴 | |
| [ ] | 1.7 | Save to `data/processed/*.parquet` and create `README_data.md` | 🔴 | |
| [ ] | 1.8 | Add `observation_date`, `available_date`, source, and download date | 🔴 | |
| [ ] | 1.9 | Add automated tests for schema, duplicates, gaps, chronology, and coverage | 🔴 | |
| [ ] | 1.10 | Verify total return/adjusted prices, currency, calendar, and units for each source | 🔴 | |
| [ ] | 1.11 | Build the common sample for all strategies and document the start of each series | 🔴 | |
| [ ] | 1.12 | Create a small, publishable demonstration dataset with no restricted data | 🔴 | |

## Step 2 — Exploration & Estimation

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 2.1 | Compute descriptive statistics by asset (return, volatility, Sharpe, skewness, kurtosis, max drawdown) | 🟡 | |
| [ ] | 2.1b | Create a correlation heatmap and rolling equity/bond correlation | 🟡 | |
| [ ] | 2.2 | Three-year rolling Σ: sample vs. Ledoit-Wolf | 🔴 | |
| [ ] | 2.2b | Demonstrate instability (composition maps, LN3 lab) | 🟢 | |
| [ ] | 2.3 | Select, implement, and document a conservative μ estimator | 🔴 | |
| [ ] | 2.4 | Set the reference Sharpe ratio SR_T and perform sensitivity analysis | 🔴 | |
| [ ] | 2.5 | Implement reproducible baselines: equal-weighted, GMV, and 60/40 | 🔴 | |
| [ ] | 2.6 | Run diagnostics for normality, autocorrelation, historical ES, and subperiod stability | 🟡 | |
| [ ] | 2.7 | Add unit-consistency tests: daily/annual, variance/volatility, simple/log/excess return | 🔴 | |
| [ ] | 2.8 | Compare sample/LW by conditioning, weights, turnover, and realized-volatility error | 🔴 | |
| [ ] | 2.9 | LN3 option: use the resampled frontier as a demonstration, not a production requirement | 🟢 | |

## Step 3 — Client Profile: Baseline, Then Adaptive Questionnaire

> The **fixed, transparent profile** takes priority. The adaptive engine remains a bonus until its real-world validity and stability have been demonstrated.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 3.0a | Define capacity, tolerance, knowledge, objectives, and constraints separately | 🔴 | |
| [ ] | 3.0b | Draft the fixed 10–15-question baseline using neutral wording | 🔴 | |
| [ ] | 3.0c | Define fully explainable scoring rules and capacity caps | 🔴 | |
| [ ] | 3.0d | Freeze and document the JSON `profile` output format | 🔴 | |
| [ ] | 3.0e | Conduct user testing for comprehension, edge cases, and test-retest stability | 🔴 | |
| [ ] | 3.0f | Display that the tool is academic and not psychometrically certified | 🔴 | |
| [ ] | 3.0g | Test profile serialization, import/export, and version compatibility | 🔴 | |
| [ ] | 3.1a | Draft the 10 Block A questions (capacity) | 🟢 | |
| [ ] | 3.1b | Draft the 20 Block B questions (tolerance, ordered scales) | 🟢 | |
| [ ] | 3.1c | Generate the 24 Block C pairs with φ_seuil on a log grid [0.5, 20] | 🟢 | |
| [ ] | 3.1d | Draft the six Block D questions (constraints) plus branching conditions | 🟢 | |
| [ ] | 3.1e | Store the question bank in `questions/bank.json` (README format) | 🟢 | |
| [ ] | 3.2a | Implement swipe likelihood (logit on ΔU, parameter λ) | 🟢 | |
| [ ] | 3.2b | Implement scale likelihood (graded response / ordered logit) | 🟢 | |
| [ ] | 3.2c | Set prior parameters for Block B items (a, b_k) | 🟢 | |
| [ ] | 3.3 | Implement the grid-based Bayesian engine (prior, update, mean/median, SD, 80% CI) | 🟢 | |
| [ ] | 3.4 | Implement adaptive selection (minimize expected posterior variance) plus block quotas | 🟢 | |
| [ ] | 3.5 | Define the stopping rule (SD < threshold or 15 questions) | 🟢 | |
| [ ] | 3.6 | Add a mirrored question, inconsistency detection, and messages | 🟢 | |
| [ ] | 3.7 | Define capacity rules → σ*_cap (maximum loss, horizon, liquidity) | 🔴 | |
| [ ] | 3.8 | Calibrate Tobin φ → σ*_tol, apply the capacity cap, then recalculate achieved volatility | 🔴 | |
| [ ] | 3.9a | Build a synthetic-client simulator (1,000 φ values, noisy responses) | 🟢 | |
| [ ] | 3.9b | Compare adaptive vs. random vs. fixed vs. 60 questions (RMSE, σ* error, % correctly classified) | 🟢 | |
| [ ] | 3.9c | Plot “error vs. number of questions” (pitch figure) | 🟢 | |
| [ ] | 3.9d | Test robustness to high noise and misspecified parameters | 🟢 | |
| [ ] | 3.10 | (Optional) Conduct a real survey of 40–60 students, recalibrate, and prune items | 🟢 | |
| [ ] | 3.11 | Compare the adaptive approach's real-world validity with the baseline, not only its internal simulation | 🟢 | |

## Step 4 — Signals

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 4.1 | Reproduce LN7: market/company polarity, abnormal volume, events, AR/AP/CAR/CAP | 🔴 | |
| [ ] | 4.1b | Reproduce at least one expected LN7 lab result before making any adaptations | 🔴 | |
| [ ] | 4.1c | Build a dated and validated company → sector mapping | 🔴 | |
| [ ] | 4.1d | Test sector aggregation as a distinct hypothesis | 🟡 | |
| [ ] | 4.1e | Test Mann-Whitney/robust regression and out-of-sample stability | 🔴 | |
| [ ] | 4.2 | Run offline FOMC classification → tone index per document | 🟢 | |
| [ ] | 4.3a | Define relative sentiment views `P`; include the Fed only if the extension is validated | 🔴 | |
| [ ] | 4.3b | Estimate `Q` on train/validation data only; disable the view if unstable | 🔴 | |
| [ ] | 4.3c | Base `Omega` on genuinely available confidence, with sensitivity analysis | 🔴 | |
| [ ] | 4.4a | Fit an HMM to standardized macroeconomic variables (select the number of states using BIC) | 🟢 | |
| [ ] | 4.4b | Use expanding-window estimation and **filtered** probabilities | 🟢 | |
| [ ] | 4.4c | Name and describe the regimes | 🟢 | |
| [ ] | 4.5 | Freeze the signal definition before the test period and maintain the experiment log | 🔴 | |
| [ ] | 4.6 | Validate StockTwits out of sample before producing BL views | 🔴 | |
| [ ] | 4.7 | Compare the HMM with a static/GMM baseline; use filtered probabilities only | 🟢 | |
| [ ] | 4.8 | Reproduce LN7 abnormal returns using a market model; do not replace it with a moving average | 🔴 | |
| [ ] | 4.9 | Decide how to handle the post-2020 period: historical demonstration or a new validated source | 🔴 | |
| [ ] | 4.10 | Compare all strategies on a common sample, then report longer histories separately | 🔴 | |

## Step 5 — Portfolio Construction

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 5.0 | Implement and test shared functions (`vol`, `risk_contrib`, `tracking_error`, `erc`, `risk_budget`, `bl_posterior`, `target_vol`) | 🔴 | |
| [ ] | 5.1 | 🏛️ Classic: constrained long-only tangency portfolio (LW Σ, conservative μ) | 🔴 | |
| [ ] | 5.2 | ⚖️ Balanced: ERC (log barrier + rescaling) | 🔴 | |
| [ ] | 5.3 | 🧠 Connected: BL (`x0` decided in 5.8, μ̃, views, μ̄, target TE) | 🔴 | |
| [ ] | 5.4 | 🌦️ Chameleon: regime budgets weighted by filtered probabilities | 🟢 | |
| [ ] | 5.5 | 📈 60/40 benchmark | 🔴 | |
| [ ] | 5.6a | Apply Tobin scaling toward σ* (plus leverage rule) | 🔴 | |
| [ ] | 5.6b | Re-optimize under client constraints (exclusions, maximum weights) | 🔴 | |
| [ ] | 5.7 | Produce analytics: weights, RC/RC*, volatility, TE, IR, concentration | 🔴 | |
| [ ] | 5.8 | Select and document the BL reference portfolio (`x0`) | 🔴 | |
| [ ] | 5.9 | Analyze BL sensitivity to `x0`, `tau`, and `Omega`, with/without views | 🔴 | |
| [ ] | 5.10 | Produce LN6 analytics: Expected Shortfall, Herfindahl, Shannon, diversification ratio | 🟡 | |
| [ ] | 5.11 | Recalculate and display the volatility actually achieved after constraints/leverage | 🔴 | |
| [ ] | 5.12 | Test constraints: weights sum to 1, bounds, classes, exclusions, explicit solver failure | 🔴 | |
| [ ] | 5.13 | Verify that BL without views reproduces the prior and that a higher-confidence view produces a stronger tilt | 🔴 | |
| [ ] | 5.14 | Add a turnover constraint/penalty if justified by the net benefit | 🟡 | |

## Step 6 — Backtest

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 6.1 | Build a monthly backtest engine (weight drift, cash at DTB3) | 🔴 | |
| [ ] | 6.2 | Run a grid of σ* × active MVP strategies | 🔴 | |
| [ ] | 6.3 | Model transaction costs and two-way turnover (0 / 10 / 25 bps) | 🔴 | |
| [ ] | 6.4 | Compute metrics (including **realized volatility vs. σ\***) and performance by regime | 🔴 | |
| [ ] | 6.5 | Test robustness to window, frequency, subperiods, and shrinkage | 🟡 | |
| [ ] | 6.6 | Export `results/*.parquet` | 🔴 | |
| [ ] | 6.7 | Add an anti-look-ahead test: weights at `t` use no subsequent returns | 🔴 | |
| [ ] | 6.8 | Report gross and net results, plus alpha/beta with HAC errors | 🟡 | |
| [ ] | 6.9 | Preserve a frozen final test; distinguish confirmatory from exploratory analyses | 🔴 | |
| [ ] | 6.10 | Verify the weight lag: decision at `t`, return earned at `t+1` | 🔴 | |
| [ ] | 6.11 | Compare over a common period; present longer histories separately | 🔴 | |
| [ ] | 6.12 | Save weights, trades, costs, diagnostics, and the configuration version for every run | 🔴 | |
| [ ] | 6.13 | Run the pipeline twice with the same seed and obtain identical results | 🔴 | |

## Step 7 — Selection & Monitoring

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 7.1 | Record the selection (profile, strategy, date, weights, amount) | 🔴 | |
| [ ] | 7.2 | Run Monte Carlo simulations (normal + block bootstrap) and calculate the probability of reaching the objective | 🟢 | |
| [ ] | 7.3 | Include historical monitoring in the MVP; enable live mode only with reliable current data | 🟡 | |
| [ ] | 7.4 | Define rebalancing rules (calendar / threshold) and alerts | 🟡 | |
| [ ] | 7.5 | Implement brief re-profiling (five questions, prior = previous posterior) | 🟢 | |
| [ ] | 7.6 | Create a downloadable client report | 🟢 | |
| [ ] | 7.7 | Add persistence through JSON export/import | 🟡 | |

## Step 8 — Web App

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 8.1 | Build a multipage skeleton (Home + four pages), **deployed by week 2** | 🔴 | |
| [ ] | 8.2 | Implement `st.session_state` (responses, profile, selection; posterior only if adaptive) | 🔴 | |
| [ ] | 8.3a | Build the Profile page (one question at a time, swipes, profile reveal) | 🔴 | |
| [ ] | 8.3b | Build the Menu page (MVP strategy cards + comparison table) | 🔴 | |
| [ ] | 8.3c | Build the Analysis page (weights vs. RC, views, backtest; regime/Monte Carlo if validated) | 🔴 | |
| [ ] | 8.3d | Build the Monitoring page (value, drift, alerts, rebalancing, export) | 🟡 | |
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

- [ ] Black-Litterman reference portfolio (`x0`): ERC, 60/40, or available market weights
- [ ] Is leverage permitted? (100% cap or up to 1.5×)
- [ ] Final list of macroeconomic variables and number of regimes
- [ ] Reference SR_T value
- [ ] Volatility caps by horizon (capacity rules)
- [ ] Risk budgets by regime (Chameleon)
- [ ] CHF option (currency risk): yes / no
- [ ] Conduct the real survey (3.10): yes / no
- [ ] Final test start date and common StockTwits period
- [ ] Code license and publishable demonstration files
