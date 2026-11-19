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

Source units and current calculation conventions are specified in
[Data Conventions](08_DATA_CONVENTIONS.md). In particular, DTB3 is a discount-basis
percent quote; the existing `/100/252` convention is only a daily cash-rate
proxy. Resolve publication timing and accrual before the final cash/financing
backtest. Adjusted price ratios are a vendor total-return proxy, not nominal
historical execution prices.

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

[Step 3.0a](19_PROFILE_DIMENSIONS.md) defines what each dimension captures and how it informs the fixed profile.

### 5.2 MVP

Begin with a fixed questionnaire of 10 to 15 questions, with transparent rules and a reproducible result. Produce a versioned JSON profile. Test edge cases and have the wording reviewed by people outside the group.

### 5.3 Adaptive — Extension

The adaptive Bayesian model is activated only after:

1. validation by simulation against fixed and random baselines;
2. a parameter-recovery test;
3. a sensitivity analysis of item parameters;
4. real user testing focused on comprehension and test-retest stability.

A simulation generated and estimated by the same model validates the code, not real psychometric validity.

### 5.4 Risk Category and Reference Volatility

The calibration derived from `phi` provides a continuous internal estimate. Capacity imposes a ceiling. The capped estimate is mapped to one of four client-facing categories: Conservative (4%–6%, reference 5%), Balanced (6%–9%, reference 8%), Growth (9%–12%, reference 10%), or Aggressive (12%–15%, reference 14%). Boundaries follow the project configuration.

The category is the recommendation presented to the client. Its reference volatility is used to select prepared portfolios. After applying constraints and the leverage cap, recalculate the ex-ante volatility actually achieved and display any deviation from both the reference and the category range. The continuous score is retained for audit and technical analysis, not presented as a precise promise.

## 6. Risk and Return Estimation

### 6.1 Covariance

Baseline: sample covariance over a rolling window. Primary model: Ledoit-Wolf. Compare conditioning, predicted/realized volatility, weight stability, and turnover.

### 6.2 Expected Returns

Never use a full-sample mean. Compare:

- shrunk rolling historical mean;
- implied returns of the reference portfolio;
- no `mu` for ERC/RB.

The choice is fixed before final evaluation and documented in the decision log.

Step 2.3's implementation default is the regularized Bayes–Stein-style
GMV-mean shrinkage rule adapted from Raf's notebook (DR-05). It uses daily
excess means and daily LW constant-correlation asset covariance over the same
trailing window, with final arithmetic annualization. It reduces cross-sectional
differences by construction; predictive superiority and final OOS validation
remain unclaimed. See [the formula, units and validation gates](13_EXPECTED_RETURNS.md).

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

### 7.1 Relative view matrix

Step 4.3a uses a labelled matrix `P` with one column per investable asset,
in portfolio order. For one approved snapshot, rank comparable scores for
the eligible sector ETFs. The strongest sector receives +1, the weakest
−1 and the remaining assets zero. The row therefore selects the difference
between the two expected asset returns. The corresponding return differential
`Q` and uncertainty `Omega` are estimated in Steps 4.3b and 4.3c.
[Black and Litterman (1992)](https://people.duke.edu/~charvey/Teaching/BA453_2006/Black_Litterman_Global_Portfolio_Optimization_1992.pdf).

Use the approved validity window of the snapshot and make a row only when
both extremes are unique and at least two eligible scores are finite. The
current company-level signal awaits historical GICS and out-of-sample
validation. The direct-ETF experiment and the FOMC baseline have no approved
predictive view. The current matrix therefore has zero rows and retains all
12 asset columns. The notebook demonstrates both shapes. Step 5.3 consumes
the empty matrix as a no-view case with the ERC equilibrium prior.

### 7.2 Expected return spread Q

Step 4.3b calibrates the spread on the realized returns of the views that
the same signal rule would have selected at each historical decision.
For each completed holding month, apply that month's row of `P` to
daily simple returns from the first NYSE close through the last close.
Take the mean daily spread for the month and omit incomplete months.
The shared cash rate cancels because the row sums to zero.

Require at least 24 training months and 12 later validation months with
eligible outcomes. The training mean must be positive, the validation mean
must also be positive, and the frozen training mean must yield a lower
validation MAE than a zero-spread forecast. Remove a row of `P` when its
view fails these checks. For the surviving views, refit the mean over
train and validation with equal weight per month and multiply by 252 to
express `Q` in annualized arithmetic units. The calibration excludes the
decision month and everything from the final-test month onward. A missing
final-test boundary leaves `Q` empty.

The notebook illustrates these rules on synthetic returns. The checks
define calibration eligibility. Predictive approval remains a separate
requirement in Step 4.6.

Step 4.6 selects the strongest and weakest observed sector scores before
joining prices. If an extreme is tied or a selected leg cannot be priced at
both scheduled closes, the month contributes no realized spread. The
company test E014 uses the project's nine [sector ETF
proxies](https://www.ssga.com/us/en/individual/capabilities/equities/sector-investing/select-sector-etfs)
and excludes sectors outside the portfolio universe. On the reused
exploratory window, the direct-tag variant E015 reverses from +0.623% per
month in training to −0.879% in validation. See the [experiment
log](06_EXPERIMENT_LOG.md) for coverage and the outstanding company test.

### 7.3 View uncertainty Omega

Take the mean squared error (MSE) of each active view's frozen training
forecast on its completed validation months. Step 4.3b supplies this error
before refitting the spread, so training fit and final-test outcomes do not
enter this uncertainty estimate. The supplied StockTwits counts do not
include classifier probabilities. Message volume may be studied as a
separate weight once a dated view has been validated.

For each row `p` of `P`, multiply the daily spread MSE by 252² so that it
matches the squared units of the annualized `Q`. Use the larger of this
quantity and the prior view variance `tau × p × Sigma × pᵀ` as the diagonal
entry of `Omega`. This conservative floor protects against spuriously
small validation errors. `Sigma` is the annualized asset covariance in
portfolio order. The current single-view rule yields a diagonal matrix.

The notebook varies the validation-error component by 0.5×, 1× and 2×
with the prior floor fixed. For one view, its weight in the posterior
spread is `prior_view_variance / (prior_view_variance + Omega)`. A lower
weight means a smaller revision toward `Q`. The current empty `P`
produces an empty `Omega`.

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

For Step 4.4a, sample the six publication-lagged FRED features at the last
scheduled NYSE session of each completed month. Fit the scaler on the
exploratory training window January 2005–December 2015. Fit diagonal Gaussian
HMMs with three and four states using 12 deterministic starts each. For each
candidate keep the converged run with the highest log-likelihood and select
the lowest BIC on the same sample. Repeat the comparison through December
2014 to check sensitivity to the training endpoint.
[hmmlearn model selection](https://hmmlearn.readthedocs.io/en/latest/auto_examples/plot_gaussian_model_selection.html).

The 132-month run selects four states (BIC 1243.94 versus 1357.70). The
120-month sensitivity run selects four as well. These fits use latest-vintage
FRED exports with modeled publication lags. Recheck the selection with
historical vintages before using regime probabilities in a backtest. The
final project test split stays open.
[ALFRED historical vintages](https://alfred.stlouisfed.org/help/downloaddata).

Step 4.4b fixes the exploratory state count at four and uses six starts
per monthly fit. For each month, refit both the scaler and the HMM on months
strictly before the observation, then apply the forward filter through the
current observation. Store the probability vector with the next NYSE
session as its availability date. Match state means between fits and the
first model in the first scaler's units, so the numerical labels have a
common reference across re-estimation.
[Rabiner's forward algorithm](https://www.ee.columbia.edu/~dpwe/e6820/papers/Rabiner89-hmm.pdf).

The exploratory run produces 24 monthly vectors for 2016–2017. The same
numerical state ranks first in all 24. Appending future observations leaves
past filtered estimates unchanged in the tested sequence. This chronology
check concerns the filtering algorithm. Historical data vintages are still
needed to remove revision leakage before backtesting.

Step 4.4c describes the same first model used to align the expanding fits.
The table uses fitted emission means in reporting units. Probability
summaries describe the fixed model on its training sample. The expanding
estimates in Step 4.4b apply to later observations.

| State in the exploratory run | Description | Representative fitted features | Dominant training months |
|---|---|---|---:|
| 0 | Expansion under financial strain | Industrial production +3.4% YoY, VIX 21.8, Baa–10y spread 3.0 pp | 39 |
| 1 | Low-inflation expansion | Inflation +1.2% YoY, production +1.6% YoY, unemployment change −0.9 pp YoY | 41 |
| 2 | Contraction and financial stress | Production −10.1% YoY, unemployment change +2.9 pp YoY, VIX 32.4 | 18 |
| 3 | Calm expansion with a flat yield curve | VIX 13.6, 10y–2y slope 0.18 pp, production +2.7% YoY | 34 |

The low-inflation state also leads all 24 exploratory filtered months from
2016–2017. Its fitted self-transition probability is effectively one in the
reference fit. This persistence limits the evidence for useful regime
switching. Revisit the labels on the historical-vintage fit before turning
them into risk budgets.

In Step 4.7, refit a four-component diagonal Gaussian mixture and the
four-state HMM on each expanding prefix, with the same scaler fitted on
that prefix. Score the next monthly macro vector with the HMM state
probabilities forecast from the preceding filtered distribution. The
static mixture uses its fitted component weights. Compare predictive log
density in transformed feature units on identical dates.
[Gaussian mixture log density](https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html#sklearn.mixture.GaussianMixture.score_samples).

On the exploratory 2016–2017 window the HMM leads on 21 of 24 months, with
a mean advantage of 0.686 nats per month. The gain falls from 1.025 in
2016 to 0.347 in 2017. The comparison measures macro density fit on revised
FRED inputs. Portfolio utility and vintage-aware validation remain open.

## 9. Backtest

The backtest has two distinct outputs. The scientific output validates the strategy with full diagnostics. The client-facing output is a versioned summary used by the prepared portfolio catalogue. It is historical evidence, not a return forecast.

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

### 9.5 Client-Facing Summary

For every `risk_band × strategy` combination, export a common-period, net-of-cost summary containing historical annualized return, realized volatility, net Sharpe ratio, maximum drawdown, and annualized cost. Export Sortino, Calmar, Expected Shortfall, turnover, concentration, tracking error, risk contributions, and subperiod results for the technical panel.

Advantages and limitations are generated from prespecified strategy characteristics and validated diagnostics. A strategy must never be called “best” solely because it has the highest historical return.

## 10. Preventing Data Snooping

- Maintain an experiment log: hypothesis, date, parameters, result, decision.
- Define the primary metrics before testing.
- Limit the number of variants.
- Do not promote a variant solely because it wins on the test set.
- Distinguish confirmatory and exploratory analyses.
- Display unfavorable results and limitations.

## 11. Application

The application does not initiate downloads or computationally intensive backtests. It loads versioned artifacts, checks their date, and displays a clear message if they are missing. Every page must work with a local demonstration dataset.

Client mode uses plain language and follows the journey defined in `07_USER_JOURNEY.md`: questionnaire, category, prepared strategy cards, selection, and monitoring. A technical panel presents formulas, assumptions, and sources for the professor. Every estimate is accompanied by a date, an uncertainty measure, and an academic disclaimer.

After selection, historical backtest results remain frozen as the evidence shown at the decision date. A separate live-monitoring layer uses the latest available prices to calculate value since selection, weight drift, current drawdown, rolling realized volatility, and rebalancing alerts. Daily end-of-day updates are sufficient.

## 12. Minimum Tests

- data: schema, dates, duplicates, NaN values, temporal availability;
- mathematics: variance, annualization, Euler, ERC, BL without views, target volatility;
- optimization: satisfied constraints, explicit solver failure;
- backtest: no future returns, correct costs, drifted weights;
- profile: edge cases, serialization, consistency of caps, deterministic category boundaries;
- catalogue: every active category-strategy pair has dated metrics, advantages, limitations, and a common comparison period;
- application: complete category-to-selection-to-monitoring flow and no crashes.
