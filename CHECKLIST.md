# RiskMatch — Project Checklist

> Working checklist for the concept review in `RiskMatch`. Phase 1 follows the agreed [client profile specification](CLIENT_PROFILE.md). Unchecked tasks require implementation or verification.
>
> The [notebook](RiskMatch_pipeline.ipynb) contains the current outline.
> Check `[x]` when the task is **completed AND verified**. Enter your initials under “Owner.”
> Legend: 🔴 critical for the grade · 🟡 important · 🟢 bonus
>
> The order and content below are starting points for the concept review.

---

## Project language

- [x] **English migration.** Project documentation, notebook, client cards, code and grouping directories use English. The course and market-data originals retain their supplied filenames and contents. The decision log records scope and checks. [Decision log](DECISION_LOG.md)

## Bias checks at each step

For each run, record the following in the H01–H07 study record or pilot report: **step, potential bias, unit and period, counts before and after, benchmark and corrected metrics, difference and uncertainty, client impact, action and residual risk**. Resample dates in blocks for time-series comparisons and whole people for questionnaire comparisons. Differences across assumptions measure sensitivity. A causal interpretation requires an independent reference. Where information is missing, record “not estimable”, identify the data needed and suspend the affected use.

| Step | Checks completed in the pilot | Checks still needed |
|---|---|---|
| 0–1 · Data | Input checksums, independent trading calendar, return reconciliation, date consistency, ALFRED vintages, WRDS and StockTwits attrition | Unadjusted prices and independent corporate actions, actual release times and display rights |
| 2–3 · Estimation and profile | Sensitivity at three forecast origins, jointly feasible allocations and a separate transfer-item bank | Recruit participants, measure agreement, dropout and stability, and calibrate risk bands |
| 4–5 · Signals and optimization | Correct zero-message polarity, resample date blocks, exclude each stock from its market factor, mask WRDS fields at the actual decision session and verify an admissible CHF entry | Full event replication, net signal tests and exclusions checked against dated holdings |
| 6–7 · Backtesting and monitoring | Two minimum-trade rules, fees and delay with orders frozen, CHF sleeve and project risk, breach severity and duration, early withdrawal and real funding needs | Observable execution, development recalibration, independent comparison and timestamped feed for online use |
| 8–10 · Application and delivery | Acceptance criteria and failure scenarios recorded for each step | Working Streamlit journey, user tests, pitch rehearsals and reproduction from a clean installation |

## First reproducible walkthrough

- [ ] **Profile.** Reserve two conditional trade-offs before routing. Freeze φ and the predictions before presenting the held-out items. Archive agreement, disagreement and undetermined outcomes. Present two admissible allocations in counterbalanced order. Record the choice and the reason. [Pilot protocol](CLIENT_PROFILE.md)
- [ ] **Main H01–H03 experiment.** Keep windows, currency, constraints, costs and allocation rule identical for SPY, IEF and GLD. Compare sample covariance, Ledoit–Wolf and covariance conditional on stress. Freeze a stress definition observable at decision time and a fallback to Ledoit–Wolf if too little conditional history is available. Measure error at identical weights first, then changes in weights and their cost.
- [ ] **Risk bands.** Archive the cap, horizon and risk forecast before each monthly outcome. Compare with the historical benchmark at the same dates and budgets. Report breach frequency, mean excess in volatility points given a breach, consecutive breach duration, sample sizes and uncertainty. Flag inadequate precision.
- [ ] **CHF demonstration.** Use a fictional CHF 50,000 mandate with CHF 15,000 needed in two years and an eight-year horizon for the remainder. Ring-fence the reserve once. Show two admissible allocations for the rest if available, accounting for FX and costs. Replay the withdrawal and compare holding with reallocating after an alert. Reconcile wealth and show conflicts if the target is unreachable.

- [x] **ETF benchmarks.** Run 60/40, 1/N and GMV across 72 monthly decisions from 2010 to 2015 at 0, 10 and 25 bp. Reconcile trades, fees, daily wealth and terminal capital. Perturb future data and verify that the old positions earn the execution-day return.
- [x] **Historical CHF withdrawal.** Replay the two-year withdrawal for the three benchmarks with the initial reserve, entry FX costs and dated indicative quotes. Reconcile the amount paid and remaining wealth.
- [x] **Benchmark calendar.** Record the development period and prospective ETF window in the notebook and the [research protocol](RESEARCH.md#etf-benchmark-schedule).
- [ ] **Prospective benchmark monitoring.** Starting at the final close of November 2026, record targets before each execution and archive observed values through November 2027.

### Priority extension after the first backtest — frontier stability

- [x] **Pilot entry criteria.** Check an analytic two-asset case and reconcile cash flows in the first monthly SPY/IEF/GLD backtest.
- [x] **H01 pilot.** Compare sample covariance and Ledoit–Wolf across 72 months, first by QLIKE at identical weights and then through two GMVs after trading costs. Report paired uncertainty using 3-, 6- and 12-month blocks.
- [x] **Single-origin sensitivity.** At December 31, 2015, calculate P10–P90 weights and utility regret for φ = 2, 5 and 10 with 500 joint resamples per block length. Compare holding with minimum trading inside a utility tolerance. Verify an analytic two-asset case and an infeasible cap.
- [x] **Monthly decisions.** Replay four policies in 2010–2015 for the diagnostic USD sleeve and CHF mandate. Log each review. Perturb future data and verify that past decisions are identical. Compare fees, capital, risk breaches and their severity on 71 complete CHF intervals. Isolate the final censored interval.
- [ ] **Experiment.** At each selected origin, resample asset returns jointly in blocks using only the past window. Reestimate μ and Σ, then resolve the frontier over the same risk grid. Hold the mandate, constraints, current weights and fee schedule fixed. Prespecify the block length, sensitivity variants and required Monte Carlo precision in development.
- [ ] **Decision.** For every budget and φ range, report weight dispersion, choice-switching frequency and infeasible cases. Within each reestimated scenario, measure the net utility loss of each candidate relative to that scenario’s optimum. Before validation, set an economically meaningful tolerance and a rule for selecting near-optimal allocations. Compare robust and classical proposals out of sample under the same mandate using net utility, costs and risk-band breaches.
- [ ] **Client presentation.** If different weights deliver similar utility, show multiple allocations and explain their trade-offs. Report the dispersion as estimation sensitivity and separately check realized future risk.

Dynamic correlations and regimes fall under H01–H03. Machine-learned stock selection falls under H05. Revisit reinforcement learning once the simulator reproduces cash flows and fees and the benchmark reallocation policy has been validated.

## Work sequence and research decisions

The following technical steps outline the tasks. Follow these milestones to determine whether to proceed to the next stage. After the initial two, studies can progress in parallel depending on available resources. The strategies identified in steps 4 and 5 are viable options. The thresholds and final catalog remain open. [Models, tools, variations, and decision rules](RESEARCH.md)

- [ ] Before each estimate, complete the [method sheet](RESEARCH.md#pre-estimation-study-record): plausible bias, hypothesis, diagnosis, decision in case of failure, and residual limit.
- [ ] Part 01 – For H01-H07, follow the appropriate path and archive the eight validation steps, any inapplicable controls, and corrections. [Audit Matrix](RESEARCH.md#applying-the-part-01-decision-map)
- [ ] Record the source, the target, the reference, the variations, the economic threshold, and the chronological breakdown before each trial.
- [ ] Assess the actual availability, currency, costs, and historical context; reproduce the 60/40, 1/N, and GMV references.
- [ ] H01 — Does covariance shrinkage improve allocations? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H02 — Does forecasting risk improve exposure decisions? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H03 — Do macroeconomic conditions help explain bonds and cross-asset dependence? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H04 — Do valuation ratios and macro variables forecast returns better than the historical mean? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H05 — Does WRDS stock selection add value after costs? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H06 — Does a view derived from LN7 add information? Archive the comparison, uncertainty and decision under the protocol.
- [ ] H07 — Do rebalancing bands preserve gains after costs? Archive the comparison, uncertainty and decision under the protocol.
- [ ] A — Publish forecast errors, out-of-sample interval coverage and width, subperiod results and the register of all trials.
- [ ] B — Build the constrained net frontier and compare variants at equal risk. Remove macro signals, ML and dynamic covariance one at a time.
- [ ] C — For each mandate, test risk-band breaches, withdrawal shortfall probability and costs. Decide on catalogue inclusion and version the exclusions.
- [ ] Display the frontier, available options, the project target, and tracking from selection; verify timestamp, flow, and reallocation with confirmation.

### Methods and tools by hypothesis

| Study | Comparison and tools | Decision criteria |
|---|---|---|
| H01 | Compare sample and Ledoit–Wolf covariance under identical optimization constraints using NumPy, scikit-learn and CVXPY. | Future risk forecast error, conditioning, weight stability and net utility relative to the benchmark. |
| H02 | Fixed versus variance-managed exposure. Compare EWMA with GARCH-t/GJR using arch, then DCC across three asset classes. | QLIKE for next month’s variance. Test the value of changing exposure after costs separately. |
| H03 | Yield curve alone versus curve plus macro factors using PCA, VAR and local projections in scikit-learn/statsmodels. Distinguish exposures and lagged forecasts. | Intervals, stability and out-of-sample R². Use the model for attribution only if forecasting fails. |
| H04 | Expanding historical mean versus linear predictor and ridge in chronological windows. | Out-of-sample R², quantile score and net gain. Use Clark–West for suitable nested linear models under squared loss. |
| H05 | Use DuckDB for the WRDS panel. Compare NYSE sorts, elastic net and boosting, training on complete months. | Rank correlation, monotonicity, factor alpha, costs and microcap sensitivity. Compare long-only sleeves at the same equity weight. |
| H06 | LN7 event study, market model and Black–Litterman with and without a view using statsmodels and NumPy. | Check event overlap, dated coverage and net gain under the same tracking-error budget. |
| H07 | Use the same signal with monthly, quarterly or band-triggered trades. Keep a pandas ledger of purchases, sales and half-spreads. | Break-even cost, net savings, risk drift and withdrawal coverage. |

Running the econometric comparisons. The primary horizon proposed is the following month. Supplementary horizons, hyperparameters, numerical tolerances, and economic thresholds should be entered into the configuration before the test. The output names indicated in the steps refer to deliverables to be produced.

| Test | Calculation and diagnostic recipe for determination |
|---|---|
| H01 | Compare sample covariance with shrinkage on identical past daily returns. Specify the paper’s constant-correlation target or sklearn’s scaled identity. At fixed weights, aggregate variances to match the units of the sum of future squared daily returns. Then rerun the optimization with each matrix. |
| H02 | Estimate EWMA, Student-t GARCH(1,1) and GJR on past data using `arch_model`. Check convergence and standardized residuals using Ljung–Box and ARCH-LM. Aggregate daily forecasts to the monthly horizon under explicit assumptions. With positive forecast variance v and realized proxy y, compare log(v)+y/v. Separately evaluate managed exposure after costs. |
| H03 | Compare curve slope alone with a regression using dated macro factors for IEF/TLT. For VAR, choose lags on training data, check roots and residuals and identify innovations before computing impulse responses. Repeat across identification orderings. Keep real rates/dollar versus gold and oil/copper versus sectors exploratory until confirmed. |
| H04 | At every origin record the expanding mean, OLS forecast and ridge forecast tuned in internal validation. Out-of-sample R² = 1 − candidate sum of squared errors / benchmark sum of squared errors. For non-nested models compare paired losses using an appropriate long-run variance. Use Clark–West only when nesting and squared loss justify it. |
| H05 | Each month construct lagged book-to-market, gross profitability, asset growth and 12–1 momentum. Freeze the NYSE breakpoint rule and recompute cutoffs on each eligible date. Compare a simple ranking, elastic net and boosting using blocks of months. Report monthly Spearman correlations, quantile returns, sector/factor betas and alpha with time-series inference. Repeat without microcaps and with observable spreads. Evaluate the long-only sleeve separately. |
| H06 | Estimate the market model before the event and calculate abnormal and cumulative abnormal returns over a frozen window. Adjust inference for clustered events. Reproduce LN7 before introducing views. Build P, Q and Ω using information available at the time. Compare BL with/without views at the same tracking-error budget, including dates with no signal. |
| H07 | On the same signal path compare monthly, quarterly and no-trade-band rules tuned in validation. Apply half-spread and fees to amounts actually traded from drifted weights. Find the unit cost at which the relative net benefit disappears. Report risk-band breaches and uncovered withdrawals. |

Perform benchmark tests before the initial backtest. Freeze the [comparison contract H01–H07](RESEARCH.md#comparison-protocol-for-h01h07) for each variation. Preserve the outputs from these examples and any deviations from the expected result.

- [ ] **Accounting and timing.** Specify the execution price and first holding interval. With closing prices only, a signal known after close t and executed at the next close earns nothing over the preceding interval. Starting from 100, a proportional charge of 0.20 followed by a 10% gain on the remainder yields 109.78. Also test an all-cash portfolio and a no-trade case.
- [ ] **Risk and utility.** Over 20 sessions with forecast daily variance 0.0001, integrated variance is 0.002 and its square root is 4.472%. For 3% certain versus equally probable −10%/+20%, indifference gives φ = 16/9. Compare both utilities on each side of the threshold. Handle equal variances without division. In the theoretical Tobin case, φ = 4 and a forecast annual Sharpe of 0.4 give 10% annual volatility before constraints.
- [ ] **Tests and selection.** For identical forecasts and a common target, the loss difference is zero. Return “test undetermined” when its variance is zero. If the benchmark predicts perfectly, the out-of-sample R² denominator is zero. Show absolute errors. Test a null signal and a known signal in synthetic data. Record seed, replication count and Monte Carlo error.
- [ ] Validity of the decision: Verify the direction of the effect, the minimum economic size, dependence, and multiplicity. If the model improves prediction without improving the mandate after costs, limit its use to diagnosis. When making any post-test corrections, retain the original result and identify the new analysis as exploratory.

### Quantitative and econometric workflow for each study

Follow the branches of the [map Part 01](<Theory/Methodology/Decision_Maps/Partie_01.svg>). In each experiment’s record, note the references to the map used, the diagnosis, its evidence, the decision, and any branches that are irrelevant, along with their reason. The eight validation checks should be followed in the order listed below. Any result that is not sufficiently precise remains undetermined.

- [ ] **P1–P7 · Define the measure.** Reconcile adjusted prices with total returns around dated events, count dividends and delisting returns once, and trace observation, release, order and execution dates. Compound the portfolio’s simple returns. Match the risk-free rate to the currency and period. Fix the benchmark and costs. Document calendar differences and unavailability. Limit prospective interpretation if macro revisions remain.
- [ ] **F0–F7 · Specify before estimation.** Define unit, population, target, horizon, H0, alternative, statistic, meaningful magnitude and expected direction. Record sample sizes before and after filters, missing data, distributions, influential values and correlations. Justify transformations, estimation and standard errors. Plot residuals and quantiles. Check collinearity, dependence and stability. Correct the specification on development data and archive both versions.
- [ ] **A/D/E · Cross-section, panel and factors (H05).** Distinguish date-specific sorts, pooled regressions and Fama–MacBeth premia. For a pooled model, examine firm and time effects and dependence by firm and month. Compare appropriate clustered standard errors. Test mean monthly premia using time-series inference. For first-pass estimated betas, justify a Shanken correction or bootstrap both passes. GRS tests joint alphas with tradable factors under its assumptions. Report the diagnostic long–short spread and investable long-only result.
- [ ] **B · Time series and risk (H02/H04).** Inspect ACF/PACF and select lags and windows on training data. Compare ADF and KPSS with a justified intercept/trend, then examine structural breaks. For GARCH compare Gaussian and Student-t innovations. Check convergence, admissibility, persistence and standardized residuals using Ljung–Box on levels and squares and ARCH-LM. If unstable, compare EWMA. Simulate under H0 to check small-sample bias for persistent predictors.
- [ ] **C · Systems and dependence (H01/H03).** For VAR, check root stability and residual autocorrelation. Record ordering, identification and bootstrap impulse-response bands. For integrated series examine cointegration rank and deterministic terms before fitting VECM. Verify covariance symmetry, eigenvalues and conditioning. Test forecasts at identical weights before measuring the impact of weight changes. Granger tests incremental predictive information. Causal interpretation needs separate identification.
- [ ] **E3/Q1–Q3 · Events and learning (H05/H06).** Separate estimation and event windows. Check clustered announcements and overlaps. Test a compatible time placebo. Date every signal, target and feature. Fit imputation, scaling, PCA, selection and hyperparameters inside each inner window. Keep all firms for a month together. For text models, record the version, training-data cutoff and coverage.

| Card validation | Proof or decision to record for RiskMatch |
|---|---|
| 1 · Chronology (V1/V20/V17/V21) | Trace dated signal → order → executable price → return. Purge overlapping labels and justify any embargo. Changing future data must preserve past weights. Reserve an untouched period. |
| 2 · Measurement (V2/V10/V3) | Prespecify loss: QLIKE for variance, quantile score for quantiles, CRPS as a score and PIT as a calibration diagnostic for a full continuous distribution. For an 80% band report width, coverage, the exceedance sequence and sample counts by regime. |
| 3 · Comparison (V4–V6/V14/W12/V11) | Align forecasts on identical dates. Use Diebold–Mariano with appropriate long-run variance for non-nested forecasts and Clark–West for a nested linear extension under squared loss when assumptions hold. Check calibration bias and paired Sharpe ratios. Test any model combination as a separate variant. |
| 4 · Multiplicity (V7–V9/V15/W8) | Declare the test family, horizon and primary metric. Log every trial. Apply Holm to confirmatory hypotheses. When choosing the best of many models, justify SPA or a deflated Sharpe ratio and report dispersion across trials. |
| 5 · Uncertainty (V12/V13) | Distinguish parameter intervals, forecast intervals and wealth distributions. Fit bounds using past data. If using conformal calibration, explain temporal dependence and drift, then check future coverage. |
| 6 · Robustness (V18/W14 and relevant W branches) | Test falsifications, competing factors, sample endpoints, extremes, omission of a crisis, delays and fees. Justify external validation in another market or period. Document the change that reverses the conclusion. |
| 7 · Verification (V19/W13/V16) | Simulate plausible dependence and measure false-positive rates under H0 and power at the stated minimum effect. Check the optimizer against a known analytic case. A wide interval cannot establish absence of an effect. |
| 8 · Release and monitoring (V22–V24) | Keep divergent replications, versions, negative findings and independent reproductions. Before deployment, set drift review frequency, the alert rule and the rule for reverting to the benchmark. |

Conditional branches: Utilize classification tools for a categorical target, counting tools for counted events, and causal tools (A4/D4) if a credible identification strategy exists. Activate high-frequency tools (B7) only with corresponding data and execution questions. Add any new branch to the register before testing.

## Course coverage and required checks

This table covers 61 Markdown course notes and the [EMiF decision tree](<Theory/Course_Notes/EMiF_Arbre_Decision.svg>) in the [course folder](Theory/Course_Notes/). Parallel versions of one week are grouped together. Each row identifies the decision it informs and the evidence required. Mark it complete after execution or after documenting why a conditional branch does not apply.

| Sources | Step and work to be done | Expected proof or decision |
|---|---|---|
| EMiF 1–4 | Steps 1–2. Construct total returns in the mandate currency. Examine moments, tails and dependence. If mean returns show dependence, compare a parsimonious AR with the historical benchmark. | Per asset, report frequency, sample size, missing data, ACF and out-of-sample errors. Failure to reject Ljung–Box leaves nonlinear dependence possible. |
| EMiF 5–7, tree | Examine the integration order, rank, and stability before VAR or VECM. For each macroeconomic scenario, apply the same shock to each eligible portfolio, based on its weights at the decision date. | Shock matrix × portfolio, contributions of assets and interval. Indicate the units of the shock, identification order, and vulnerability to other orders. |
| EMiF 8 | Steps 2 and 5. Distinguish between historical or predictive probabilities and risk-neutral probabilities used for valuation. If option prices fall within a view, treat the implied indicator as a predictor to test. | Clearly label the measure and horizon of each probability presented to the client. Reserve valuation models to a specific instrument or identified assumption. |
| EMiF 9–11 | H01–H02. Compare EWMA with GARCH/GJR, then constant correlation with DCC at identical weights. Use HAR on realized volatility or jump decomposition only if observation frequency supports that measure. | QLIKE, standardized residuals, covariance admissibility and portfolio risk forecast error. Identify proxies based on closing prices. |
| EMiF 12–13 | H03. Differentiate between a persistent break and a recurrent pattern. Alternatively, compare linear beta and downward beta, or quantile regression for negative returns. Freeze a threshold or developing quantile. In a latent state, calculate the filtered probability at each origin using only the estimable parameters. | Analyze the effect sizes by state, stability of the threshold, and quantile loss relative to the historical quantile. Reserve smoothed probabilities and dated breaks for retrospective analysis across the entire series. |
| QARM II LN1–3 | Step 5: Construct the boundary under constraints, test shrinkage and weight stability. Differentiate Sharpe ratio of the portfolio, market beta, and relative active risk compared to the benchmark. | For each increment of φ, publish eligible options, along with weight sensitivity and tracking error relative to the benchmark and defined horizon. |
| QARM II LN4–7 | H06 and Step 5. Recover the no-view Black–Litterman prior, perturb NLP view confidence and test its incremental benefit. For ERC, compute volatility contributions RCᵢ = wᵢ(Σw)ᵢ / σₚ for σₚ > 0. | Verify that contributions sum to σₚ, compare relative contributions with budgets and explain constraint-induced deviations. Match each message to the first executable order. Compare BL with the same prior and no signal. |
| Advanced Data Analytics, introduction, lectures 3, 4, 6, 11, 12, 14 | Versioning the Python pipeline. Adjust imputation, normalization, PCA, and clustering within each time window. For regimes, compare an observable indicator to the clustering and verify the stability of groups between windows. For a binary, observable target, compare the predicted probability to its historical frequency. | Freeze transformations and assignments before the next prediction. Archive out-of-sample errors and, for probabilities, Brier score and calibration. Categories derived from the questionnaire require independent validation before being used as supervised labels. |
| Advanced Data Analytics 7–10, 13 | Variations. GPR for a conditional range based on several factors, if coverage and width can be assessed against simple regression. Sequential network if historical data allows for multiple distinct validation windows. RL after validating the simulator and the benchmark. PINN if a future valuation problem specifies an equation and its boundary conditions. | Record for each trial the target, available volume, benchmark, and calculation cost. For a pre-trained network, also document the deadline for its data. |
| Guides on factors, sorts, predictability and costs, plus literature.md | H02, H04, H05 and H07. Replicate the study definition and benchmark before adapting it. Repeat sorts with value weighting and NYSE breakpoints. Distinguish half-spread cost estimates from measured decision-to-execution price differences. | Record universe, period, available inputs, published result, reproduction, deviations and net result for each paper. Strategy choices cited in the bibliography apply to the referenced study. |
| W1, W5 and SAAM W11 | Steps 3, 5, and 8. Transform a strict ethical exclusion into a verifiable constraint. For an ETF, use the dated composition, the exclusion rule, and issuer coverage. | Report covered, excluded, and unknown positions. If the unknown prevents a strict exclusion from being verified, mark the position as unverifiable for that mandate. Distinguish declared preference, measured exposure, and impact attribution. |
| W2, W3 and W4 (all guides) | H03. Relate activity, inflation, central bank decisions and geopolitical shocks to sector equities, bonds and gold. Distinguish reported changes from surprises relative to the consensus available before release. | Without dated consensus data, study a change or an explicit scenario. Compare sensitivities on identical dates and measure the currency effect in the client’s currency. |
| W6–W8, W10 | H04–H05. Distinguish earnings from cash flow. Test a quality indicator when its line items and release dates exist. Examine banks separately when industrial-company ratios lose meaning. Freeze technical rules and compare against simple momentum after costs. | Document inputs, revisions, counts by sector and exclusion effects. Keep scenario valuations in sensitivity analysis while their forecasting power is undetermined. |
| W9, W13 (all guides) | Steps 3 and 7. Apply asset–liability matching to simulate withdrawals at maturity. Counterbalance gain/loss framing of economically equivalent choices during the pilot. Measure presentation effects, financial capacity and stated tolerance separately. | Report frequency and size of withdrawal shortfalls. For cards, record participants per variant, choice-switching rate and uncertainty. Clarify contradictory responses. |

- [ ] Before the pilot and the initial backtest, complete the relevant fields in the study sheets and clearly specify the expected deliverable. For each conditional data source, record the coverage, availability date, and fallback solution.
- [ ] Before modifying an allocation, compare the candidate and the benchmark on the same dates, with the same constraints and costs. Also, archive negative tests and the precision of the effect. If the gain is limited to historical description, preserve the result to explain the portfolio.

### Checks from the expanded QARM II notes

Both versions of each chapter address the same topic. The following assessments utilize the explanations and additional examples found in the Quant projet folder’s files.

- [ ] [LN1](<Theory/Quant_Project/QARM2_LN1_Cours_Explique copie 2.md>) — Solve the frontier with CVXPY on the same universe and check the unconstrained case against its analytic solution. In each risk-aversion band, maximize μ_net − φσ²/2 over the feasible frontier. Test an unattainable objective and check that the interface explains the conflict.
- [ ] [LN2](<Theory/Quant_Project/QARM2_LN2_Cours_Explique2 copie.md>) — Fix the benchmark before estimation. Calculate predicted tracking error from active weights and Σ and compare it with the realized standard deviation of active returns. Benchmark replication must yield zero tracking error and an undefined information ratio.
- [ ] [LN3](<Theory/Quant_Project/QARM2_LN3_Cours_Explique copie 2.md>) — Perturb μ and Σ separately within a past window. Measure weight changes, turnover from current holdings and cost. Compare shrinkage with turnover constraints at the same target risk. Distinguish bootstrap frontier dispersion from Michaud’s strategy of averaging weights at corresponding points.
- [ ] [LN4](<Theory/Quant_Project/QARM2_LN4_Cours_Explique copie 2.md>) — Distinguish the Black–Litterman reference portfolio’s implied aversion from the client’s range of φ. Test a relative view with a zero-sum row of P. Increase its variance in Ω and verify that the posterior mean approaches the prior when it is the only view.
- [ ] [LN5](<Theory/Quant_Project/QARM2_LN5_Cours_Explique copie 2.md>) — Test the ERC solver with a positive-definite covariance matrix, uniform correlations and equal budgets. Weights should be proportional to inverse volatilities. Repeat with heterogeneous correlations and directly check realized risk contributions.
- [ ] [LN6](<Theory/Quant_Project/QARM2_LN6_Cours_Explique copie 2.md>) — For a long-only invested portfolio calculate the effective number of holdings 1/Σwᵢ² and the diversification ratio (Σwᵢσᵢ)/σₚ when σₚ > 0. Two identical equal-weighted assets give 2 and 1 respectively. If diversification is a mandate objective, compare the maximum-diversification portfolio with equal risk contribution under the same constraints.
- [ ] [LN7](<Theory/Quant_Project/QARM2_LN7_Cours_Explique copie 2.md>) — On dated StockTwits data, reproduce volume peaks and plot cumulative abnormal return (CAR) and cumulative abnormal polarity (CAP) separately, then their means by event type. Replicate the course Mann–Whitney test and account for event dependence. For H06 form the signal before the order with no knowledge of the future type. Compare net value with no-view BL.

Evidence already obtained in the notebook (steps 4 and 5)

- [x] LN1–LN3. Verify the analytical solution for three values of φ, including a scenario of inaccessible returns and a benchmark identical to the benchmark. Compare the effects of perturbing μ, shrinkage, and a rotation ceiling, all under the same estimated risk limit. Validation of the categorization remains open.
- [x] LN4–LN6. Verify the return to the prior when confidence decreases, ERC weights under uniform correlation, budgets with empirical covariance, and the case of two identical positions.
- [x] LN7. Compare the reconstructed peaks with the events provided in the assessable observations before 2016. Examine the CAR and CAP around the peaks, the rank test on J−1, and the common dates across multiple events.
- [ ] LN7 / H06. Explain the discrepancies with the provided labels, estimate the uncertainty taking into account temporal grouping, and compare BL with and without an adjustment for expenses over a defined period.
- [x] H03. Apply a constant interest rate scenario to the five demonstration compositions, reconcile contributions by asset, and calculate the sensitivity range. Predictive power and regime studies remain open.

### Checks from guides 00–34

The [correspondence by decision](RESEARCH.md#applying-the-34-guides-to-riskmatch) links each chapter to studies, conditional uses, or client mandates.

- [x] **H06 event selection.** Calculate cumulative polarity from day −20 to day −1 using only that window. After excluding zero-message polarity observations, the notebook has 490 eligible events. Of these, 351 also have complete plots through day +20. Verify that both calculations agree at day −1 on those 351 windows. Event type is assigned on day 0.
- [x] **H02 risk.** During 2010 development, record daily historical 95% VaR and ES using the prior 252 sessions for five allocations frozen at year-end 2009. Test empirical ES with ties and fractional tail mass. Report frequency, longest run and mean loss beyond the threshold in basis points.
- [x] **Withdrawal capacity.** On the synthetic CHF 50,000 mandate, verify accounting, loss ordering, reserve and temporary inability to sell. Measure the liquidity shortfall at the deadline even if total wealth exceeds the withdrawal.
- [ ] **Before model selection.** Freeze validation and test dates. Compare quantile losses with the benchmark on the same dates and VaR/ES pairs with a suitable joint score. Estimate uncertainty in score differences by blocks. Keep breach diagnostics by subperiod and document low tail precision.
- [ ] **In the pilot.** Record risk-band status and eligible options before and after each follow-up card. Evaluate its contribution on held-out trade-offs. Report counts and response times by branch. People routed to different cards already differ in their profiles.
- [ ] **Before rebalancing.** Replay the same mandate with fees, FX and settlement dates, then disrupt the data feed. Check that the reserve remains accessible and a stale forecast triggers the planned fallback. Also archive the hold decision to measure the benefit of intervening.

## Step 0 — Organization & Setup

**Possible biases.** Retrospective protocol selection, parameters chosen after inspecting results and changes in the execution environment.

**Measurement and response.** Freeze hypothesis, unit, period, benchmark, minimum meaningful effect and variants before each trial. Archive input and dependency versions. Count subsequent changes and classify the trial as exploratory if its rule changes.

**Procedure**

- [ ] Following the QARM supports and the mandate, create a line for each test in `experiments.csv`: ID, source, responsible party, target, horizon, benchmark, variant, metric, minimal useful effect, assumptions, status. Mark previously reviewed periods as exploratory.
- [ ] Reporter within `config.yaml`, covering schedules, currencies, universes, windows, costs, seeds, and versions. Following the inventory of dates (step 1), freeze the development/validation/test branches with the configuration commit. A previously examined period requires independent validation.
- [ ] Re-run an example from the lab in a new environment. Archive the command, versions, inputs, expected result, actual result, and any explanation of discrepancies.

- Method: Before any estimation, define for each hypothesis the scope, the decision date, the target, the reference point, the minimum useful gain, and the exit rule. Freeze the chronological separation and version changes.
- Tools: Git for version history, YAML for configuration, and a log of experiences for decision-making.
- Verification and deliverable. Another person should be able to find the dated specification and identify the periods that have already been explored.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 0.1 | Ask the professor the four questions (2026 requirements, StockTwits data, expected backtest, topic approval) | 🔴 | Raf |
| [ ] | 0.2 | Record the presentation date and finalize the schedule | 🔴 | |
| [ ] | 0.3 | Create the GitHub repository and invite all five members | 🔴 | |
| [ ] | 0.4 | Create the repository structure (see README) | 🔴 | Codex |
| [ ] | 0.5 | Set up a shared Python environment (initial `requirements.txt`, same Python version) | 🔴 | |
| [ ] | 0.6 | `config.yaml`: tickers, dates, SEED, assumptions | 🟡 | Codex |
| [ ] | 0.7 | Complete the six labs (LN1–LN5, LN7) → foundation for the engine | 🔴 | |
| [ ] | 0.8 | Assign team roles | 🔴 | |
| [ ] | 0.9 | Freeze the MVP scope and include adaptive profiling in the MVP and classify HMM/FOMC as extensions | 🔴 | Raf |
| [ ] | 0.10 | Start the decision register and experiment log | 🔴 | Codex |
| [ ] | 0.11 | Select and freeze the train/validation/test periods before producing final results | 🔴 | |
| [ ] | 0.12 | Verify licenses and publication rights for data, models, and materials | 🔴 | |
| [ ] | 0.13 | Enable GitHub CI (`pytest` on Python 3.12) | 🔴 | |
| [ ] | 0.14 | Protect `main`: pull request plus review by another member | 🟡 | |
| [ ] | 0.15 | Define “done”: code + test + documentation + reproducible result + review | 🔴 | |
| [ ] | 0.16 | Select the code license and add `LICENSE` before publication | 🟡 | |

## Step 1 — Data Collection

**Possible biases.** Calendar gaps, filled prices, revisions, duplicates, unpublished data and survivorship.

**Measurement and response.** Run the raw-to-prepared audit. Record initial and retained counts, missingness by source/date/asset, maximum calculation difference and reason for each exclusion. Reject an order if an XNYS session is missing. Distinguish observed and carried-forward FX and disclose assumed timestamps.

**Procedure**

- [ ] Generating `series_catalogue.csv` data from sources like ETF/FRED/WRDS/StockTwits. By field: provider, identifier, frequency, unit, currency, adjustments, vintage, earliest usable date, license, missing values, and replacement rule.
- [ ] Build the panel using `pandas.merge_asof(direction="backward")` or a DuckDB ASOF join on the **availability date**. Verify PERMNO/GVKEY and validity intervals. Compare counts before and after joining by year and sector. Isolate duplicates and ambiguous matches.
- [ ] Recalculate simple, excess and client-currency returns on selected dates. With CHF per USD verify (1+R_USD)(1+R_FX)−1. Test a split, dividend, delisting, holiday and after-close announcement. Export the dated panel and exception report.

- **Method.** Separate observation, publication, availability and execution. Join historical CCM links and accounts point in time. Handle delistings, splits, dividends, currencies and trading sessions. Document removals and imputations.
- Tools: DuckDB for CRSP, pandas or Polars for date joins, Parquet for tables, SHA-256 for the manifest.
- Verification and deliverable. Generate coverage and attrition by series/date. Inject a future publication into a test case and verify its exclusion. Without reliable versioning, limit the macro conclusion or test a conservative timeframe.

- [x] File Integrity – Verify the order and uniqueness of dates, the positivity and finiteness of ETF prices, and the fingerprints of the common manifest (reproducible notebook cell).

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 1.1 | Download adjusted prices for the 12 ETFs plus SPY (yfinance, 2005 →) | 🔴 | Raf / Codex |
| [ ] | 1.2 | Download DTB3 (FRED) and convert it to a daily rate | 🔴 | Raf / Codex |
| [ ] | 1.3 | Download FRED macroeconomic series (T10Y2Y, BAA10Y, VIXCLS, CPIAUCSL, UNRATE, INDPRO) | 🟡 | Raf / Codex |
| [ ] | 1.3b | Apply the publication lag to monthly series | 🟡 | Raf / Codex |
| [ ] | 1.4 | Obtain the professor's StockTwits data | 🟡 | Vlad |
| [ ] | 1.4b | Build the company → GICS sector mapping table | 🟡 | |
| [ ] | 1.5 | Obtain FOMC texts (or the gtfintechlab dataset) with publication dates | 🟢 | |
| [ ] | 1.6 | Clean the data: business-day index, NaNs, duplicates, outliers (market bundle and provisional direct-ETF sentiment) | 🔴 | Raf / Codex |
| [ ] | 1.7 | Save to `data/processed/*.parquet` and create `README_data.md` | 🔴 | Raf / Codex |
| [ ] | 1.8 | Add `observation_date`, `available_date`, source, and download date | 🔴 | Codex / Vlad |
| [ ] | 1.9 | Add automated tests for schema, duplicates, gaps, chronology, and coverage (market bundle and provisional direct-ETF sentiment) | 🔴 | Codex |
| [ ] | 1.10 | Verify total return/adjusted prices, currency, calendar, and units for each source | 🔴 | Codex |
| [ ] | 1.11 | Build the common sample for all strategies and document the start of each series | 🔴 | Codex |
| [ ] | 1.12 | Create a small, publishable demonstration dataset with no restricted data | 🔴 | Codex |

<a id="gics-dependency"></a>
### Historical GICS dependency (1.4b)

Review the coverage and dates of historical GICS before validating 1.4b.
This does not block market-data cleaning, equal-weight/GMV/60-40, Classic, ERC,
or a no-views BL baseline. Direct-ETF sentiment is a separate provisional input,
not a replacement for company-sector aggregation.

Return here before completing:

- **4.1c**: dated company-to-sector mapping — historical GICS and identifier links are required.
- **4.1d**: the GICS-based test requires validated 4.1c.
- **4.3a and 4.6**: company-derived BL views and their out-of-sample validation — require the mapped signal; direct-ETF views must be tested and labelled separately.
- **5.3**: activating company-sentiment BL requires validated views from 4.6.
- **1.11 and 6.11**: finalize common coverage again when company-derived sentiment is introduced.

## Step 2 — Exploration & Estimation

**Possible biases.** Window-sensitive means, unstable covariance, tail errors and confusion between USD and CHF risk.

**Measurement and response.** Compare conditioning, fixed-weight forecasts and paired scores using a block bootstrap. Repeat at multiple origins and retain jointly feasible allocations. Evaluate VaR and ES on more crises before selection. Present sleeve and project risk in the mandate currency.

**Procedure**

- [ ] Calculate CAGR (Compound Annual Growth Rate) for individual assets and for the portfolio, as well as volatility, maximum drawdown, recovery rate, historical ES (Expected Standard Deviation), and the number of losses used for the ES calculation. Compare distributions and correlations over different periods; also plot pairs during crises.
- [ ] For a series in levels use `statsmodels.tsa.stattools.adfuller` (H0: unit root) and `kpss` (H0: stationarity under the chosen specification). Choose intercept/trend from the economic mechanism. If the tests disagree, examine breaks and transformations and retain both diagnostics.
- [ ] At each month’s last available quote, estimate covariances on the same past window. Check symmetry, eigenvalues, conditioning and units. At fixed weights compare forecast and realized variance before evaluating optimized weight turnover. Save `diagnostics.parquet` and the estimator record.

- Method: Calculate compound and excess returns, volatility, maximum losses, recovery time, ES, and correlations using shrinkage and EWMA over the same historical window. Examine distributions, breakpoints, residuals, and the contribution of each class.
- Tools. NumPy/pandas for moments and trajectories, scikit-learn for shrinkage (specify the target), statsmodels for diagnostics and HAC errors, block bootstrap for intervals.
- **Verification and deliverable.** Report results by asset and period. Check units and conditioning. Compare forecast with realized variance, weight stability and out-of-sample turnover.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 2.1 | Compute descriptive statistics by asset (return, volatility, Sharpe, skewness, kurtosis, max drawdown) | 🟡 | Raf / Codex |
| [ ] | 2.1b | Create a correlation heatmap and rolling equity/bond correlation | 🟡 | Raf / Codex |
| [ ] | 2.2 | Three-year rolling Σ: sample vs. Ledoit-Wolf | 🔴 | Raf / Codex |
| [ ] | 2.2b | Demonstrate instability (composition maps, LN3 lab) | 🟢 | |
| [ ] | 2.3 | Select, implement, and document a conservative μ estimator — regularized Bayes–Stein-style mean | 🔴 | Raf / Codex |
| [ ] | 2.4 | Estimate and stress-test the reference Sharpe for the theoretical Tobin check | 🔴 | Raf / Codex |
| [x] | 2.5 | Implement reproducible baselines: equal-weighted, GMV, and 60/40 | 🔴 | Codex |
| [ ] | 2.6 | Run diagnostics for normality, autocorrelation, historical ES, and subperiod stability | 🟡 | Codex |
| [ ] | 2.7 | Add unit-consistency tests: daily/annual, variance/volatility, simple/log/excess return | 🔴 | Codex |
| [ ] | 2.8 | Compare sample/LW by conditioning, weights, turnover, and realized-volatility error | 🔴 | Codex |
| [ ] | 2.9 | LN3 option: use the resampled frontier as a demonstration, not a production requirement | 🟢 | |

## Step 3 — Client profile (product phase 1)

**Possible biases.** Framing effects, familiarity with repeated lotteries, selective dropout and false psychometric precision.

**Measurement and response.** Counterbalance sides and sequence. Freeze predictions before independent transfer items. Report coverage, agreement, retest, dropout and elapsed time by participant. Resample whole participants for intervals. Leave the band undetermined if evidence is insufficient.

**Procedure**

- [ ] Version `questions/bank.json` and its transitions. For each financial trade-off, calculate 2(μB−μA)/(σ²B−σ²A) over the same horizon. Handle equal variance, dominance, indifference and failed comprehension. Factual answers carry no score.
- [ ] Use pytest to traverse common routes, corrections and contradictory branches. Test an imminent withdrawal despite high tolerance, a mandatory exclusion and an indeterminate profile. Changing capacity alone must preserve tolerance.
- [ ] Export `profile.json` with version, goal, cash flows, currency, constraints, φ range, uncertainty and reason. In the human pilot, measure comprehension, time, dropout and retest agreement using a band transition matrix. Document recruitment and order effects.

- **Method.** Use four intake screens, then 15 common cards and conditional branches drawn from the 60-card bank. Infer a φ range from understood return–risk choices and their indifference thresholds. Record capacity, exclusions and behavioral observations separately.
- **Tools.** Versioned JSON bank, Python routing engine, pytest branch checks, pilot questionnaire and one-week retest.
- **Verification and deliverable.** Verify card counts and reachability, loop-free routing, the effects of corrections, consistent outputs and category stability. Report uncertainty where the boundary is ambiguous.

Follow the [phase 1 specification](CLIENT_PROFILE.md). The typical pilot length is an observation target, not a stopping rule.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 3.0a | Design four factual intake screens outside the card bank | 🔴 | Codex |
| [ ] | 3.0b | Separate goals, willingness, financial capacity, hard exclusions, preferences and follow-up | 🔴 | Codex |
| [x] | 3.1a | Draft 2 comprehension cards (1 common) and 20 financial choices (8 common) | 🔴 | Codex |
| [x] | 3.1b | Draft 14 loss-sensitivity cards (4 common in two pairs) and 10 drawdown-response cards (2 common) | 🔴 | Codex |
| [x] | 3.1c | Draft 8 conditional financial-situation cards and 6 follow-up cards; select one closing card | 🔴 | Codex |
| [x] | 3.1d | Version the bank and validate 60 unique cards, 15 common and 45 conditional | 🔴 | Codex |
| [ ] | 3.2 | Estimate a range for φ from understood financial choices only; handle indifference, skipped and misunderstood choices | 🔴 | Codex |
| [ ] | 3.3 | Pilot four tolerance bands; allow adjacent bands or insufficient evidence | 🔴 | Codex |
| [ ] | 3.4 | Encode answer-specific triggers across families, common coverage and correction of earlier answers | 🔴 | Codex |
| [ ] | 3.5 | Stop when no useful probe remains; retain uncertainty after two inconclusive probes per issue | 🔴 | Codex |
| [ ] | 3.6 | Require two distinct comparisons and client confirmation for each reported behavioral observation (maximum two) | 🔴 | Codex |
| [ ] | 3.7 | Assess project capacity from dated withdrawals, reserves and obligations; apply hard constraints separately | 🔴 | Codex |
| [ ] | 3.8 | Translate tolerance to a portfolio risk band subject to project capacity; preserve the original tolerance and recheck achieved volatility | 🔴 | Codex |
| [ ] | 3.9 | Test routing, termination, scoring independence, incomplete profiles, export/import and revised answers | 🔴 | Codex |
| [ ] | 3.10 | Pilot comprehension, observed duration, typical 20–25 cards, value of probes and one-week retest | 🔴 | Codex |
| [ ] | 3.11 | Record calibration and limitations; compare common-only vs adaptive results before claiming validity | 🔴 | Codex |

## Step 4 — Signals

**Possible biases.** Macroeconomic simultaneity, revised releases, self-selected message spikes and correlated events.

**Measurement and response.** Separate contemporaneous scenarios from lagged predictions. Record the data vintage actually available. Compare with no-view models and estimate event uncertainty using date blocks. Also validate on non-event dates and with the asset excluded from its own market indicator.

**Procedure**

- [ ] For each of H01–H07, apply the H01–H07 matrix recipe at the top of the checklist. Write one line for each forecast or decision, including the origin, horizon, universe, model/version, maximum training date, value, reference, and realization date.
- [ ] Construct the variables using only the data that was originally accessible. Re-run the calculation after perturbing future data; require identical past signals. For PCA/ML, adjust the transformation and estimator within each inner time step.
- [ ] Combine the achievements after the deadline, calculate paired losses, and export `forecasts.parquet`. For each chosen variant during validation, write the pattern, the implementation cost, and its authorized use (description, forecast, or allocation).

- Method: Follow the H01–H07 matrix above, according to the question. Distinguish between contemporary exhibitions, delayed forecasts, and identified shocks. Reproduce the lab before any adaptation for StockTwits; also record negative tests.
- Tools: statsmodels for regressions, VAR, and event studies, arch for GARCH, scikit-learn for PCA, regularization, and boosting. Adjust each transformation within the learning window.
- Verification and deliverable. Export predictions, along with associated benchmarks and paired losses; maintain separately descriptive and predictive usage. Document unstable models or insufficient coverage.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 4.1 | Reproduce LN7: market/company polarity, abnormal volume, events, AR/AP/CAR/CAP | 🔴 | |
| [ ] | 4.1b | Reproduce at least one expected LN7 lab result before making any adaptations | 🔴 | |
| [ ] | 4.1c | Build a dated and validated company → sector mapping — [requires 1.4b](#gics-dependency) | 🔴 | |
| [ ] | 4.1d | Test sector aggregation as a distinct hypothesis — [requires mapped companies](#gics-dependency) | 🟡 | |
| [ ] | 4.1e | Test Mann-Whitney/robust regression and out-of-sample stability | 🔴 | |
| [ ] | 4.2 | Run offline FOMC classification → tone index per document | 🟢 | |
| [ ] | 4.3a | Define relative sentiment views `P`; include the Fed only if the extension is validated — [GICS dependency for company-derived views](#gics-dependency) | 🔴 | |
| [ ] | 4.3b | Estimate `Q` on train/validation data only; disable the view if unstable | 🔴 | |
| [ ] | 4.3c | Base `Omega` on genuinely available confidence, with sensitivity analysis | 🔴 | |
| [ ] | 4.4a | Fit an HMM to standardized macroeconomic variables (select the number of states using BIC) | 🟢 | |
| [ ] | 4.4b | Use expanding-window estimation and **filtered** probabilities | 🟢 | |
| [ ] | 4.4c | Name and describe the regimes | 🟢 | |
| [ ] | 4.5 | Freeze the signal definition before the test period and maintain the experiment log | 🔴 | |
| [ ] | 4.6 | Validate StockTwits out of sample before producing BL views — [distinguish company and direct-ETF signals](#gics-dependency) | 🔴 | |
| [ ] | 4.7 | Compare the HMM with a static/GMM baseline; use filtered probabilities only | 🟢 | |
| [ ] | 4.8 | Reproduce LN7 abnormal returns using a market model; do not replace it with a moving average | 🔴 | |
| [ ] | 4.9 | Decide how to handle the post-2020 period: historical demonstration or a new validated source | 🔴 | |
| [ ] | 4.10 | Compare all strategies on a common sample, then report longer histories separately | 🔴 | |

## Step 5 — Portfolio Construction

**Possible biases.** Extreme targets, infeasible models, fees charged to cash and confusion between the client cap and the optimal allocation’s risk.

**Measurement and response.** Check the budget, estimated costs and risk from entry. Compare the two minimum-trade rules on net utility difference, ex-ante breaches and weight dispersion. Report an unverifiable mandatory ESG exclusion if holdings coverage is unknown.

**Procedure**

- [ ] Collect the φ range, protected amounts, cash flows, currency, drifted weights, μ, Σ, fees and restrictions. Reserve essential commitments. Sweep risk budgets with CVXPY, maximizing expected return less trading costs subject to budget, bounds, exclusions and volatility ≤ cap. Align the horizons for return and cost.
- [ ] Verify solver status, constraint residuals, the weight sum, variance wᵀΣw and monotonicity of optimal value as the budget increases. Check the Tobin case with one risky asset and cash. Identify the binding conflict for infeasible mandates.
- [ ] Re-evaluate the boundary using block samples. Export `frontier.parquet` (date, budget, weight, cost, anticipated net yield, volume, uncertainty, active constraints). Cross-reference the points using U for the φ range, plot the required target, and maintain several feasible options.

- **Method.** Calculate 1/N, 60/40 and GMV, then sweep constrained volatility budgets for the net frontier. Compare ERC, mean–variance, BL with/without views and scenario ES, changing one component at a time.
- Tools. CVXPY for convex programs, NumPy for risk contributions, and block bootstrap for sensitivity of the frontier to estimates.
- Verification and deliverable. Archive weights, active constraints, reached risk, costs, and utility within the φ range. Verify feasibility, the monotonicity of the boundary, and the Tobin theoretical case. Report an unattainable objective.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 5.0 | Implement and test shared functions (`vol`, `risk_contrib`, `tracking_error`, `erc`, `risk_budget`, `bl_posterior`, `target_vol`) | 🔴 | |
| [ ] | 5.1 | 🏛️ Classic: constrained long-only tangency portfolio (LW Σ, conservative μ) | 🔴 | |
| [ ] | 5.2 | ⚖️ Balanced: ERC (log barrier + rescaling) | 🔴 | |
| [ ] | 5.3 | 🧠 Connected: BL (`x0`, implied and posterior means, target TE) — [company-view prerequisite](#gics-dependency) | 🔴 | |
| [ ] | 5.4 | 🌦️ Chameleon: regime budgets weighted by filtered probabilities | 🟢 | |
| [x] | 5.5 | 📈 60/40 benchmark | 🔴 | |
| [ ] | 5.6a | Verify the Tobin special case, then solve the full net frontier under client constraints for each feasible risk budget | 🔴 | |
| [ ] | 5.6b | Re-optimize under client constraints (exclusions, maximum weights) | 🔴 | |
| [ ] | 5.6c | Build the versioned `risk_band × strategy` prepared portfolio catalogue | 🔴 | |
| [ ] | 5.7 | Produce analytics: weights, RC/RC*, volatility, TE, IR, concentration | 🔴 | |
| [ ] | 5.8 | Select and document the BL reference portfolio (`x0`) | 🔴 | |
| [ ] | 5.9 | Analyze BL sensitivity to `x0`, `tau`, and `Omega`, with/without views | 🔴 | |
| [ ] | 5.10 | Produce LN6 analytics: Expected Shortfall, Herfindahl, Shannon, diversification ratio | 🟡 | |
| [ ] | 5.11 | Recalculate and display the volatility actually achieved after constraints/leverage | 🔴 | |
| [ ] | 5.12 | Test constraints: weights sum to 1, bounds, classes, exclusions, explicit solver failure | 🔴 | |
| [ ] | 5.13 | Verify that BL without views reproduces the prior and that a higher-confidence view produces a stronger tilt | 🔴 | |
| [ ] | 5.13b | For each plausible φ, compare U = μ_net − φσ²/2 at the same horizon and in the same currency. Plot near-optimal solutions and frontier uncertainty. Test minimum risk for a target return and the infeasible case. | 🔴 | |
| [ ] | 5.13c | Convert flows and positions to the currency of the funding need. For a mandatory exclusion, check dated holdings, flag inadequate coverage and remove incompatible proposals. | 🔴 | |
| [ ] | 5.14 | Add a turnover constraint/penalty if justified by the net benefit | 🟡 | |

## Step 6 — Backtest

**Possible biases.** Look-ahead leakage, optimistic execution, assumed fees, low power and multiple testing.

**Measurement and response.** Record decisions, orders, executions, costs in the mandate currency and actual exposure. Test future-data perturbations, holding, fees of 0/10/25 bp and a one-quoted-session delay. Report breach size, frequency and duration, subperiods and confidence intervals for paired differences. Reserve an independent test before selection.

**Procedure**

- [ ] Replay each order with positions, cash, valuations, execution prices, dividends, FX, financing and commissions. Verify wealth conservation. No trade incurs zero trading fees. Buying 10% and selling 10% at 10 bp costs 2 bp.
- [ ] Experiment A compares forecasts on identical dates. B changes one element of the benchmark allocation at comparable risk budgets. C replays each mandate’s cash flows. Report gross and net outcomes, subperiods and paired differences with block intervals.
- [ ] Export `trades.parquet`, `weights.parquet`, `metrics.parquet`, and record of decisions. Freeze the selected variant before the final test. If the specified economic benefit disappears after fees or depends on a single crisis, log the limit and re-evaluate its use in the catalog.

- **Method.** Use nested rolling validation with whole dates. Purge overlapping targets. Simulate weight drift and trades at the next execution. Test 0/10/25 bp per amount traded, delays and exclusion of crisis years.
- Tools: Python/pandas for the engine, Parquet for logged data, statsmodels and temporal bootstrapping for comparisons, Holm’s method for multiple testing.
- **Verification and deliverable.** Compare forecasts, allocations and mandates separately. Publish net performance history, interval coverage, risk-band breaches, losses and uncertainty over a common period. Reserve the final test for the frozen specification.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 6.1 | Build a monthly backtest engine (weight drift, cash at DTB3) — define cash timing and accrual conventions | 🔴 | |
| [ ] | 6.2 | Run the four risk-band reference targets × active MVP strategies | 🔴 | |
| [ ] | 6.3 | Model transaction costs and two-way turnover (0 / 10 / 25 bps) — verify rate units and financing conventions | 🔴 | |
| [ ] | 6.4 | Compute metrics (including **realized volatility vs. σ\***) and performance by regime | 🔴 | |
| [ ] | 6.5 | Test robustness to window, frequency, subperiods, and shrinkage | 🟡 | |
| [ ] | 6.6 | Export `results/*.parquet` | 🔴 | |
| [x] | 6.7 | Add an anti-look-ahead test: weights at `t` use no subsequent returns | 🔴 | |
| [ ] | 6.8 | Report gross and net results, plus alpha/beta with HAC errors | 🟡 | |
| [ ] | 6.9 | Preserve a frozen final test; distinguish confirmatory from exploratory analyses | 🔴 | |
| [x] | 6.10 | Verify the first credited return from actual execution: with a signal after close t and execution at close t+1, old positions earn t→t+1, new positions first earn t+1→t+2 | 🔴 | |
| [ ] | 6.11 | Compare over a common period; present longer histories separately | 🔴 | |
| [ ] | 6.12 | Save weights, trades, costs, diagnostics, and the configuration version for every run | 🔴 | |
| [ ] | 6.13 | Run the pipeline twice with the same seed and obtain identical results | 🔴 | |
| [ ] | 6.14 | Export a common-period, net-of-cost summary for every category-strategy pair | 🔴 | |
| [ ] | 6.15 | Export the five client metrics: historical net return, realized volatility, net Sharpe, maximum drawdown, annualized cost | 🔴 | |
| [ ] | 6.16 | Export technical metrics: Sortino, Calmar, ES, turnover, concentration, TE, IR, and risk contributions | 🟡 | |
| [ ] | 6.17 | Generate prespecified, evidence-backed advantages and limitations; never rank by return alone | 🔴 | |

## Step 7 — Selection & Monitoring

**Possible biases.** Fully prefunded withdrawals, confusing cash flows with performance, mandate changes, liquidity risk and stale data.

**Measurement and response.** Replay full and partial reserves, an earlier deadline, inability to sell and a purchasing-power target. Track CHF shortfalls and forced sales. Measure sleeve and total risk after removing external flows. Separate proposal, confirmation and execution. Suspend a new order if its valuation is missing.

**Procedure**

- [ ] Start from selected holdings and separate external flows. Calculate time-weighted investment performance and the wealth path for the goal. Test a contribution with no market movement: wealth increases and investment performance is zero.
- [ ] Track weights, losses, forecast risk, persistence of breaches and quote freshness. Compare holding and reallocating at the same time after fees. Record the reason, date, new projection and client confirmation in `monitoring.parquet`.
- [ ] Simulate trajectories using multi-asset blocks and dated flows. Report the frequency and magnitude of missed deadlines, as well as the Monte Carlo error. If prices are missed, indicate the last valid closing price.

- Method: Freeze mandates, weights, and forecasts during selection. Separate inflows, outflows, and performance. Compare calendar rebalancing and persistent thresholds; estimate costs and risk before and after.
- Tools: Log of flows and positions in Parquet format, profile and selection in JSON, closing prices with timestamps; simulation in blocks for upcoming needs.
- Verification and deliverable. Reconcile the portfolio value using an example with a withdrawal. Demonstrate benchmark, drawdown, and an alert pattern; gather confirmation before reallocation.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 7.1 | Record the selection (profile, risk band, strategy, catalogue version, shown metrics, date, initial prices, weights, amount) | 🔴 | |
| [ ] | 7.2 | Distinguish the desired return from the return required by dated contributions and withdrawals. Simulate net wealth using joint blocks. Report shortfall probability and amount at maturity, Monte Carlo error and sensitivity to assumptions. | 🔴 | |
| [ ] | 7.3 | Include historical monitoring in the MVP; enable live mode only with reliable current data | 🟡 | |
| [ ] | 7.4 | Define rebalancing rules (calendar / threshold) and alerts | 🟡 | |
| [ ] | 7.5 | Use the selected follow-up preference and revisit changed circumstances before reassessing tolerance | 🟢 | |
| [ ] | 7.6 | Create a downloadable client report | 🟢 | |
| [ ] | 7.7 | Add persistence through JSON export/import | 🟡 | |
| [ ] | 7.8 | Keep frozen historical evidence separate from live performance since selection | 🔴 | |
| [ ] | 7.9 | Update value, benchmark, drawdown, weight drift, rolling risk, and alerts from latest daily prices | 🟡 | |

## Step 8 — Web App

**Possible biases.** Interface outages, stale prices, presenting exploratory results as certain and restrictions on publishing data.

**Measurement and response.** When rebuilding Streamlit, test fresh, stale and missing data and an infeasible mandate. Record age by series, failure rates and testers’ understanding of options. Display the calculation date and offer a dated historical mode.

**Procedure**

- [ ] Connect the “Profile” screens → “Frontier” → “Selection” → Tracking of versioned artifacts from the same configuration. Utilize Streamlit and its application testing; verify each unit, currency, and date displayed.
- [ ] Replay a standard scenario, a clear/objective conflict or risk, an exclusion that cannot be verified, and a missing or outdated file. Verify the messages, the absence of an incompatible proposal, and the preservation of the selection.

- Method: Present profiles, boundaries, and comparisons, followed by tracking. Load validated pre-calculated results and display date, currency, and timeframe alongside the figures.
- Tools: Streamlit, for hiding artifacts, interactive graphs, and pytest for the demo walkthrough.
- Testing an end-to-end process, including testing with stale or missing data, mobile reading and understanding the discrepancy between historical data and forecasts.

| ✓ | ID | Task | Priority | Owner |
|---|---|---|---|---|
| [ ] | 8.1 | Build a multipage skeleton (Home + four pages), target deployment date agreed at step 0.2 | 🔴 | |
| [ ] | 8.2 | Implement `st.session_state` (intake, card IDs, answers, route, uncertainty, profile, selection) | 🔴 | |
| [ ] | 8.3a | Build the Profile page (factual intake, shared cards, conditional probes, editable tolerance, project capacity and follow-up) | 🔴 | |
| [ ] | 8.3b | Show the net frontier, client zone, target, uncertainty, comparable portfolios, dated metrics and trade-offs | 🔴 | |
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

Potential biases to watch out for. Selecting an example that is overly favorable and confusion between past results and client promises.

Measuring error and taking action. Freeze examples before presentation, including a deficit and a negative result. Standardize each figure in the journal using the same currency. Time the demo and test a withdrawal change in real-time.

**Procedure**

- [ ] Link each pitch figure to its experiment ID, period, currency and output source. Prepare the client scenario, two allocations and an explanation of a negative finding. Have another member reproduce a figure and time both rehearsals.

- Method: To replay a mandate in 15 minutes: requiring two valid assessments, a historical shock, forecasting with uncertainty, and follow-up. Prepare a contradictory question for each decision.
- Tools: Streamlit application, a hypothetical scenario, a timer, and a local copy of the results for the demonstration.
- **Verification and deliverable.** Complete two timed rehearsals and trace each figure presented to an experiment and its period.

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

Potential biases to watch out for: Non-reproducible results or the dissemination of private information.

Error measurement and action. Re-execute in a clean environment with authorized data, verify fingerprints and numerical discrepancies. Distinguish between tests being executed, pending checks, and display restrictions. Document the fallback if an API is missing.

**Procedure**

- [ ] Starting from the base, the frozen environment, and the demo game. Execute the tests, the pipeline, and the application; compare diagrams, weights, and measurements against the frozen outputs, with documented numerical tolerances. Also, test the private WRDS pathway with authorized access separately.
- [ ] Deliver the README for initial launch, configuration, record of decisions, publishable results, Streamlit link, and coverage limits. Schedule the next data review and define when to pause a release or return to the baseline.

- Method: Have another member reproduce the pipeline and customer journey from a clean environment; verify the data distribution limits.
- Tools: Git tags, frozen dependencies, CI/pytest, a manifest for identifying versions, and a playable demo.
- Verification and deliverable. Archive the version, parameters, artifacts, reproduction discrepancies, and decisions. Verify access to the code, the application, and the offline scenario.

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

- [ ] Choose the Black-Litterman reference portfolio (`x0`) and the sensitivity benchmark
- [ ] Decide whether to permit leverage and set any borrowing spread
- [ ] Final list of macroeconomic variables and number of regimes
- [ ] Selecting Sharpe Beach for Tobin’s theoretical control; selecting the client area on the constrained net boundary.
- [ ] Volatility caps by horizon (capacity rules)
- [ ] Risk budgets by regime (Chameleon)
- [ ] Choose validated FX series and dates before presenting results in CHF
- [ ] Choose participants and timing for the phase 1 pilot (3.10)
- [ ] Establish the dates for tests H01-H07 and the common StockTwits period. The three ETF benchmarks have their own separate schedule.
- [ ] Code license and publishable demonstration files
