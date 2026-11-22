# RiskMatch — the project from client interview to allocation review

RiskMatch is an English-language web app built around one person's financial goal. A client should be able to answer three questions after using it. How much risk am I willing and financially able to take? Which combinations of net return and risk appear attainable for my goal, and how uncertain are they? Once I choose an allocation, what would justify changing it?

A successful outcome can be two defensible alternatives, a decision to hold, or an explanation that the original goal cannot be funded under the stated constraints. This guide explains how the team reaches those decisions. The [checklist](CHECKLIST.md) gives the numbered implementation tasks, the [notebook](RiskMatch.ipynb) records calculations and the [journal](DECISION_LOG.md) records decisions.

## Before the three product phases

### Step 0. Define what research could change (checklist chapter 1)

Start with a question whose answer affects a decision. For example, does shrinking the covariance matrix bring a portfolio's realized risk closer to the risk shown to the client? Register the paper or QARM lab, eligible assets, target, horizon, data available at decision time, benchmark, variants, primary error measure and minimum improvement that would justify adoption. Distinguish reproduction on the original sample from adaptation to a new market or client mandate.

Once coverage is known, freeze the development, validation and independent evaluation periods. A period the team has already explored can supply development evidence. Record amendments and failed trials so the best-looking variant can be interpreted in context. Use a versioned experiment register, configuration, pinned Python environment, pytest and eventually Git and CI. Start by mapping the applicable course brief to the optimization exercises, Streamlit app, reproducible repository and 15-minute pitch.

## Phase 1. Understand the client

### Step 1. Turn the goal into a financial mandate (checklist 2.1)

Four factual screens collect the goal, spending currency, horizon, starting capital, planned contributions, withdrawal amounts and dates, household reserve, desired return, exclusions and preferences. Allow ranges and unknown values. A hard ethical exclusion removes an instrument from eligibility. A preference can influence the comparison among eligible alternatives.

Consider a home buyer with CHF 50,000 and a CHF 15,000 payment due in two years. If the entire payment must be secured today and there is no external funding or other reserve, CHF 35,000 remains available for market exposure. If future savings will cover part of the payment, explicitly reconcile those savings before reducing the reserve. Employment and family circumstances matter through concrete exposures such as unstable income, dependants or employer stock concentration.

The report distinguishes willingness to take risk, capacity to withstand losses, desired return and the return mathematically required to fund the goal. Solve for the required return using the stated cash-flow timing when the inputs permit it. A missing target amount can leave that calculation open while still allowing a meaningful discussion of risk.

### Step 2. Use adaptive swipe cards to estimate tolerance (checklist 2.2)

The design calls for 60 scenarios including 15 common items. The typical route aims for roughly 20–25 scenarios in 5–10 minutes. Human testing must establish actual duration. A scenario can take several gestures. Present one statement at a time, with right for yes, left for no, and a way to pass. Retain the same meaning on a keyboard and a phone.

| Card family | Question the evidence can answer | How the route uses it |
|---|---|---|
| Comprehension | Can the client identify the lowest possible balance? | Explain an error and offer a second practice example. Persistent difficulty leaves tolerance undetermined. |
| Risk and return | Which certain outcome is preferable to a gamble with specified outcomes and probabilities? | Each understood choice bounds the aversion parameter under the one-year model. Use an additional threshold inside a wide or open interval when it can clarify the result. |
| Loss comparisons | Does the response change repeatedly when the final balance can fall below the initial stake? | Use paired scenarios and a clarifying follow-up before reporting an observation. |
| Decisions after a decline | Would the client reduce exposure, and for what reason? | Route a liquidity need to financial constraints and discomfort to a behavioral follow-up. |
| Constraints and monitoring | Which assumptions need correction, and how does the client want updates? | Amend the mandate and collect a review preference. Preserve the response history. |

For example, agreeing to reduce exposure after a 15% fall has at least two plausible explanations. If the client mentions an upcoming expense, revisit withdrawal funding even when the original intake listed none. If the client reports discomfort, clarify their response to fluctuations. The same gesture can therefore lead to different financial decisions. The client can review and correct the resulting interval, constraints and interpretation.

### Step 3. Validate the interview with people (checklist 2.3)

Simulated routes check scoring, termination, corrections and display-side invariance. The deferred human pilot answers a separate question: do the extra cards improve understanding enough to justify their time? Compare the core-only estimate with the adaptive estimate on frozen choices held out from scoring. The design includes four validation choices before the result is revealed.

Measure comprehension, agreement, repeatability, interval width, dropout, time and sample size by branch. Evaluate by participant so longer routes do not give an individual greater statistical weight. People receiving different follow-ups already differ in their initial answers. Interpret branch comparisons with that selection in mind and version any revised scoring rules.

## Phase 2. Study the market and compare feasible portfolios

### Step 4. Reconstruct what was knowable at each decision date (checklist chapter 3)

Define holdings, predictors and controls separately for every study. A copper price or an inflation reading can help explain an allocation without being something the client buys. No fixed ETF count defines the product. The archived 13-series ETF panel and three-asset example belong to earlier benchmark work.

| Input | Purpose | Check before use |
|---|---|---|
| Prices, distributions, rates and FX | Total, excess and client-currency returns | Trace a split, dividend, missing quote and FX conversion by hand. |
| Macro releases and vintages | Exposures, scenarios and forecasts | Use the release available at the time. Record revisions and after-close publication. |
| WRDS security histories and accounts | Equity characteristics and factor tests | Include historical eligibility and delistings. Verify effective identifier links and accounting publication dates. |
| StockTwits, events and sector histories | Event studies and potential portfolio views | Determine what was known before the order. Audit unmatched firms, overlapping events and incomplete windows. |
| Fees, spreads and execution calendars | Investable net outcomes | Verify quote timestamps and charge costs on actual traded amounts. |

Use pandas and NumPy for transformations, DuckDB for large panels, Parquet for prepared tables and backward as-of joins for dated data. Keep hashes, units, observation and availability times, and reasons for exclusions. Compare row counts by asset and period before and after joins. Perturb a future release and verify past decisions stay identical.

An earlier audit recorded 3,689 effective sector matches among 30,082 observations and zero verified publication dates. That motivates a specific control in this workspace: verify historical publication before treating company-derived sector sentiment as an investable signal. The local import check recounts the sector fields in the supplied Parquet table. Rebuilding the link history from source and establishing release timing remain separate research tasks.

### Step 5. Describe historical outcomes and common macro shocks (checklist chapter 4)

Use simple returns for portfolio accounting, compound them to track wealth and subtract a matching cash rate when measuring excess return. With CHF per USD as the quote, the CHF gross return on a USD asset equals the USD gross return times the FX gross return. A 5% USD gain combined with a 2% dollar depreciation produces a 2.9% CHF gain.

Measure volatility, drawdown depth and recovery time, rolling dependence, historical Value at Risk and Expected Shortfall. Report tail counts and uncertainty. Attribute portfolio risk to holdings and verify that contributions reconcile. Similar volatility can accompany very different losses at the moment a client needs cash.

Apply common equity, rate, inflation and FX shocks across candidate allocations. Explain each outcome through its holdings and exposures. Repeat by subperiod and identify unstable sensitivities. A historically plausible loss under a rate shock helps explain a portfolio even when the model cannot predict the timing of the next shock.

### Step 6. Run seven decision-oriented studies (checklist 5.1)

| Study | Comparison, tools and interpretation |
|---|---|
| H01 · Covariance | Compare sample covariance with Ledoit–Wolf shrinkage using NumPy and scikit-learn. At identical weights, compare forecast variance with future realized variance. Then reoptimize with CVXPY and measure conditioning, weight stability, risk and net utility. |
| H02 · Volatility | Compare rolling variance, EWMA and Student-t GARCH, with asymmetric GJR as a sensitivity and DCC as a possible dependence extension. Use arch, check convergence and standardized residuals, aggregate to a common horizon and compare QLIKE losses. Test whether trading on the forecast adds value after costs. |
| H03 · Macro and bonds | Compare a yield-curve-only bond forecast with lagged macro factors from training-only PCA. Use regression, VAR or local projections as appropriate. Check stability and shock identification. Explore real rates/dollar versus gold and oil/copper versus sectors separately. |
| H04 · Expected returns | Compare an expanding historical mean with OLS and ridge forecasts using lagged valuation or macro predictors. Tune inside chronological folds. Evaluate paired errors, out-of-sample R-squared and quantile scores. Use Clark–West when the nested-model and squared-loss assumptions apply. |
| H05 · Equity selection | Build dated value, profitability, asset growth and 12–1 momentum characteristics from WRDS. Compare simple sorts, elastic net and boosting using whole-month blocks. Inspect Spearman rank correlations, portfolio sorts, factor alpha, microcap sensitivity and the net long-only sleeve. |
| H06 · Sentiment views | Replicate the QARM event study using a pre-event market model, volume peaks, cumulative abnormal returns and polarity. If the signal was available on time, compare Black–Litterman portfolios with and without a view at matched tracking error. Include no-signal dates. |
| H07 · Reallocation | Replay monthly, quarterly and no-trade-band rules on the same signal and cash flows. Use drifted holdings, fees and half-spreads. Compare net wealth, risk drift, withdrawal coverage and the cost at which the advantage disappears. |

Reference starting points include Ledoit and Wolf for covariance, Moreira and Muir for volatility management, Ludvigson and Ng for macro factors, Goyal and Welch for equity premium forecasts, Gu, Kelly and Xiu for equity characteristics, and Novy-Marx and Velikov for implementation costs. Record the exact reference, original test and proposed adaptation when registering each study.

### Step 7. Validate the econometrics and forecast ranges (checklist 5.2)

For time series, inspect dependence, trends and breaks. Use ACF/PACF, ADF and KPSS with a justified trend specification. For GARCH check persistence and apply Ljung–Box and ARCH-LM diagnostics to appropriate residual series. For systems check stability before reading impulse responses and cointegration before fitting a VECM. For panels justify fixed effects, Fama–MacBeth or clustered inference according to the question.

At every rolling or expanding forecast origin, learn imputation, scaling, PCA, feature selection and tuning inside the training data. Remove overlapping target windows when necessary. Compare forecasts on identical dates. Use paired errors and dependence-aware inference such as a block bootstrap. Keep a log of all variants and designate exploratory findings accordingly.

For a common target, horizon and currency, compare the baseline, individual forecasts and an equal-weight combination on the same forward origins. If learning weights, use only past out-of-fold predictions whose outcomes were available before each decision. Register the missing-forecast fallback. Include failed origins when comparing the deployed rules and evaluate after-cost allocation value separately (checklist 5.2.4).

Record the forecast origin, horizon, target, units, currency, point or interval and benchmark. For an 80% interval, report empirical coverage, width, sequence of misses and counts by regime. A very wide interval can achieve high coverage while offering the client little guidance. A next-month forecast requires fresh assumptions and validation before being used for an eight-year goal.

### Step 8. Estimate the feasible frontier and connect it to the client (checklist chapter 6)

Protect reserves first, then apply investability, liquidity, currency, concentration and ethical constraints. Compare simple equal-weight and fixed-mix benchmarks with constrained minimum variance, equal risk contribution and research-supported alternatives. Sweep risk budgets, save solver status and binding constraints, remove dominated choices and report infeasible cases. Perturb expected returns, covariances and costs, then examine whether small changes overturn the allocation.

For a portfolio with weights w, use the one-period mean–variance approximation:

    U(w, φ) = expected net return(w) − (φ / 2) × variance(w)

Use decimal units and a consistent horizon for returns, variance and the elicited aversion parameter. Evaluate alternatives across the client's plausible φ interval. There is no universal conversion from a band of aversion to a volatility or Sharpe ratio. The opportunity set and funding constraints affect the answer. Sharpe uses excess return over matching cash per unit of volatility and provides a complementary comparison.

For each eligible option show historical outcomes, a dated forecast range, a stress loss, estimated fees and the effect on the goal. If rankings change across plausible assumptions, show the competing options and the cause. If required return exceeds what the client can reasonably pursue, illustrate what changes with more contributions, a longer horizon or a revised target.

**The QARM extension.** At the same risk limit compare a fixed mix, the classical frontier and a robust allocation. If two assets have similar forecast returns but one estimate is much less precise, the robust objective can favor the better-estimated return. Estimate uncertainty using only training observations. The radius controls how much uncertainty counts; zero recovers the classical problem. Record it before seeing the evaluation period. Compare what was predicted with subsequent net utility, costs and funding outcomes.

The dual value answers a different client question: how much extra modeled objective would a very small relaxation of a binding constraint buy? Verify it by solving again near the original limit. For reverse stress, begin with the bill at its due date. A CHF 15,000 withdrawal entirely covered by accessible CHF cash survives any loss confined to the risky sleeve. A larger payment or unavailable proceeds can change the conclusion. Present that boundary alongside the allocation comparison.

### Step 9. Backtest the actual decision before catalogue admission (checklist chapter 7)

Replay information availability, signal, order, execution and first holding period in sequence. A signal formed at today's close and filled at tomorrow's close earns no return between those closes. Maintain shares, cash, FX, reserves, flows and trading costs, and reconcile gross to net wealth. Compare candidates with holding or simple rebalancing on identical dates. Check costs, crises, risk breaches, turnover, missed trades and withdrawals.

The previous design included a SPY/IEF/GLD benchmark with cost assumptions of 0, 10 and 25 basis points, development in 2010–2015, retrospective comparison through October 2026 and a proposed prospective window from December 2026 through November 2027. This illustrates how to document a single study. Verify inputs and preregister any prospective replay before its first decision in the new workspace.

Admit a strategy only after reviewing independent performance, uncertainty, implementation costs, mandate compatibility and data permissions. Record rejected candidates and descriptive-only results alongside admitted ones.

### What each result establishes

| Decision | Evidence | Correction if evidence fails |
|---|---|---|
| Are adaptive cards worth the time? | On the same participants compare core and adaptive predictions on unchanged, held-out choices. Track prediction coverage, time and independently confirmed funding corrections. | Revise or remove low-value probes and retain an unresolved tolerance estimate when necessary. |
| Does robust optimization help this client? | Freeze the mandate; compare with a feasible fixed mix and the classical frontier using identical reserves, currency, fees and executable dates. | Correct any benchmark mismatch, then rerun. If a material net gain remains unproven, retain the simpler eligible policy. |
| Can we connect horizons? | Document the one-year hypothetical choice, monthly review signal and dated household cash-flow path. Evaluate each against its own target. | Use explicit long-horizon funding scenarios and disclose uncertainty. A failed or expired return signal sends the allocation back to its registered baseline. |
| Should this person trade? | Check funding and hard constraints first, then evaluate the paired net benefit against a prespecified practical margin. | For an eligible current holding, hold when evidence is inconclusive. A breached mandate prompts a separate feasibility review and client confirmation. |

In the demonstration, changing only risk tolerance may change sleeve weights while leaving the reserve intact. Moving a payment ahead of a confirmed contribution can increase the reserve even if every card answer stays the same. Show both counterfactuals to the client.

## Phase 3. Monitor the selected allocation

### Step 10. Show what happened after selection (checklist 8.1)

Store the confirmed mandate, weights, quantities, cash, date, currency and model version. Start with authorized closing prices and FX. Define refresh timing and behavior for missing, corrected or stale quotes. Show the last valuation timestamp.

Chart wealth, deposits and withdrawals, net time-weighted performance, drawdown, current weights and progress toward the goal. A CHF 15,000 withdrawal reduces account value by CHF 15,000. At unchanged market prices, it generates zero investment loss. The interface must make both facts clear.

### Step 11. Compare holding with rebalancing (checklist 8.2)

A new withdrawal, changed personal circumstances, allocation drift or a risk breach can trigger review. Compare holding with the proposed trade at the same decision time. Show projected costs, turnover, liquidity and expected effect on the goal. Suspend proposals when valuation inputs are stale. Ask for confirmation and record accepted trades, declines and hold decisions. Later, those records let the team evaluate whether intervening helped.

## Delivery and evidence in this workspace (checklist chapter 9)

For the course, demonstrate one investment strategy end to end: turn a client's dated withdrawal into a reserve, screen eligible assets, sweep risk limits with constrained mean–variance optimization, compare with a simple allocation and show whether weights change under covariance or cost assumptions. Let the client change an input in Streamlit and inspect the result. Link the working app and GitHub code and rehearse a 15-minute client pitch including live questions. Use the CHF 50,000 / CHF 15,000 withdrawal as one reproducible example. H01–H07, extended forecasting and ongoing monitoring remain on the broader product roadmap. Select extensions for the presentation when their measured effect changes the client decision.

The previous iteration reported an implemented profile, simulated routes, local historical experiments and a synthetic portfolio walkthrough. The workspace now includes imported local inputs, a reproducible file and return check, and illustrative notebook calculations. See the [data inventory](data/README_data.md) for the empirical scope. Human calibration is deferred. Historical results, tested features and strategy admissions require evidence attached to the new checklist before being marked complete here.

Exercise the full browser journey with a feasible goal, an uncertain profile, an infeasible goal and a stale feed. Reproduce public examples from a fresh checkout and review permissions before sharing. Build the course pitch around one client's mandate, the alternatives, the uncertainty that matters to their choice and the evidence that would justify a future change.
