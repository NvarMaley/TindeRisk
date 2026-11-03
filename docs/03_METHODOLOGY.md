# Scientific and Technical Methodology

## 1. General Principle

The pipeline follows a strict rule: **define, implement, test, validate, and only then expose in the application**. An unvalidated feature remains hidden or is marked as experimental.

## 2. Information Clock

For each observation, store:

- `observation_date`: the economic period or market date described;
- `available_date`: the first date on which the information could have been used;
- `source` and `download_date`;
- transformations and any revisions.

At rebalancing date `t`, the engine reads only rows for which `available_date <= t`. Monthly macro series are lagged by their publication delay. Regime probabilities are filtered, never smoothed. Parameters are estimated over a window ending before the decision.

## 3. Data Protocol

### 3.1 Universe

- Equities: nine historical sector ETFs.
- Diversifiers: intermediate- and long-term government bonds, and gold.
- Cash: three-month T-bill.
- Benchmark: 60% SPY, 40% IEF.

### 3.2 Controls

1. Verify currency, time zone, frequency, and adjusted prices.
2. Detect duplicates, gaps, and extreme returns.
3. Never forward-fill prices; limit forward-filling to macro data that have already been published.
4. Document series start dates and the universe actually available.
5. Produce a coverage table and a quality report.

### 3.3 Returns

- Simple returns for portfolio aggregation.
- Log returns may be used for econometric diagnostics.
- Excess returns when a formula requires the risk-free rate.
- Annualization consistent with the frequency, noting that the square-root-of-time rule is an approximation under temporal dependence.

## 4. Pre-Model Diagnostics

For each asset and for the benchmark: mean, volatility, Sharpe ratio, skewness, kurtosis, Jarque-Bera, autocorrelations, Ljung-Box, maximum drawdown, and historical Expected Shortfall. Examine rolling correlations and crisis subperiods.

These diagnostics are not used to select models opportunistically. They are used to verify assumptions and interpret limitations.

## 5. Client Profile

### 5.1 Separate Dimensions

- Capacity: horizon, liquidity, financial stability, maximum loss.
- Tolerance: preference among risk-return combinations.
- Knowledge/experience: understanding of products and risk.
- Constraints: exclusions, maximum weight, leverage, ESG.
- Objective: preservation, growth, income, or a quantified goal.

### 5.2 MVP

Begin with a fixed questionnaire of 10 to 15 questions, with transparent rules and a reproducible result. Produce a versioned JSON profile. Test edge cases and have the wording reviewed by people outside the group.

### 5.3 Adaptive — Extension

The adaptive Bayesian model is activated only after:

1. validation by simulation against fixed and random baselines;
2. a parameter-recovery test;
3. a sensitivity analysis of item parameters;
4. real user testing focused on comprehension and test-retest stability.

A simulation generated and estimated by the same model validates the code, not real psychometric validity.

### 5.4 Target Volatility

The calibration derived from `phi` provides an initial target. Capacity imposes a ceiling. After applying constraints and the leverage cap, recalculate the ex ante volatility actually achieved and display any deviation from the target.

## 6. Risk and Return Estimation

### 6.1 Covariance

Baseline: sample covariance over a rolling window. Primary model: Ledoit-Wolf. Compare conditioning, predicted/realized volatility, weight stability, and turnover.

### 6.2 Expected Returns

Never use a full-sample mean. Compare:

- shrunk rolling historical mean;
- implied returns of the reference portfolio;
- no `mu` for ERC/RB.

The choice is fixed before final evaluation and documented in the decision log.

## 7. StockTwits Signal and Black-Litterman

1. Reproduce the polarity measure from course LN7.
2. Reproduce abnormal volume, events, and abnormal polarity as the residual of the market model; a moving average is not equivalent.
3. Aggregate from company to sector using a dated mapping and prespecified weighting.
4. Define the signal before examining the test period.
5. Test the signal-return relationship using an event study/regression and a robust test. Contemporaneous raw polarity is not assumed to be predictive.
6. Estimate `Q` using only the available history.
7. Link `Omega` to a genuinely available and documented confidence measure.
8. Verify that a weak view produces a small tilt and that no views reproduce the prior.

Because the course's StockTwits coverage ends in 2020, the signal is historical by default. A current view requires a new source with appropriate rights, timestamps, and a validation protocol. The primary comparisons use a period common to all strategies; longer histories are presented separately.

FOMC tone is a separate extension. It must not be combined with the StockTwits signal until its dating protocol and out-of-sample value have been established.

## 8. Strategies

### 8.1 Baselines

- Equal-weighted portfolio over the available universe.
- 60/40 benchmark.

### 8.2 Classical

Tangency portfolio or long-only mean-variance portfolio with bounds, Ledoit-Wolf covariance, and a prudent `mu`. Also present GMV to diagnose sensitivity to `mu`.

### 8.3 Balanced

ERC using a convex/log-barrier problem, followed by rescaling. Invariants: positive weights, weights sum to one, and equal relative contributions within numerical tolerance.

### 8.4 Connected

Black-Litterman with an explicit reference portfolio, relative sector views, documented confidence, and a target tracking error. Provide sensitivity to the prior and to `tau`.

### 8.5 Non-Equal Risk Budget

An option within the core only if the previous three methods have been stabilized. Budgets must come from a prespecified economic rule, not from a search for the best backtest.

### 8.6 Regimes

Extension. First compare descriptive GMM/HMM, select the number of states on the training set using BIC and stability, and then use only filtered probabilities. Test a static version as the baseline and measure the gain net of costs.

## 9. Backtest

### 9.1 Split

- Initial estimation period.
- Validation period for fixing hyperparameters and rules.
- Frozen final test set, consulted once for the primary result.

If the sample is too short, use a walk-forward procedure with clearly defined windows. Never use a random split.

### 9.2 Date Loop

At each date: load the available information, estimate, produce target weights, allow previous weights to drift, calculate trades, apply costs, and then record the subsequent performance. Weights at date `t` may earn only returns occurring after `t`.

### 9.3 Costs

Report gross and net results. Use a 0/10/25 bps linear baseline and two-way turnover. If the data permit, add spread and impact as robustness checks. Test a no-trade band.

### 9.4 Metrics

- annualized return, volatility, and Sharpe ratio;
- maximum drawdown, VaR, and Expected Shortfall;
- turnover and costs;
- tracking error, information ratio, beta, and HAC alpha;
- predicted versus realized volatility;
- weight and risk concentration;
- weight stability;
- results by subperiod, without selecting subperiods after the fact.

## 10. Preventing Data Snooping

- Maintain an experiment log: hypothesis, date, parameters, result, decision.
- Define the primary metrics before testing.
- Limit the number of variants.
- Do not promote a variant solely because it wins on the test set.
- Distinguish confirmatory and exploratory analyses.
- Display unfavorable results and limitations.

## 11. Application

The application does not initiate downloads or computationally intensive backtests. It loads versioned artifacts, checks their date, and displays a clear message if they are missing. Every page must work with a local demonstration dataset.

Client mode uses plain language. A technical panel presents formulas, assumptions, and sources for the professor. Every estimate is accompanied by a date, an uncertainty measure, and an academic disclaimer.

## 12. Minimum Tests

- data: schema, dates, duplicates, NaN values, temporal availability;
- mathematics: variance, annualization, Euler, ERC, BL without views, target volatility;
- optimization: satisfied constraints, explicit solver failure;
- backtest: no future returns, correct costs, drifted weights;
- profile: edge cases, serialization, consistency of caps;
- application: complete demonstration flow and no crashes.
