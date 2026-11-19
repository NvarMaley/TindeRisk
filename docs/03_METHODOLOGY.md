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

### Shared portfolio functions

`src/optim.py` uses labelled weights and covariance in a common asset order.
Volatility and tracking error use the same horizon as the covariance. Euler
contribution to volatility for asset `i` is `w_i * (Sigma @ w)_i / vol`.
The risk-budget solver minimizes the convex log-barrier objective via exact
coordinate updates, then normalizes to unit invested weight. It requires
positive budgets summing to one and positive definite covariance. ERC uses
equal budgets.

The Black–Litterman helper returns the posterior expected excess returns.
An empty view set returns the prior exactly. Active views use the innovation
`Q - P @ prior` and solve the linear system with covariance
`P @ (tau * Sigma) @ P.T + Omega`. The portfolio optimizer will apply the
strategy's reference and tracking-error rules in Step 5.3.

The shared target-volatility helper scales a fully invested long-only sleeve
against cash. The maximum risky exposure and the per-ETF cap can limit the
achievable risk, which is recomputed on the scaled holdings. Step 3's profile
allocation uses this same function.

The Step 5.0 notebook verifies the formulas on synthetic inputs and checks a
756-session market snapshot ending 31 December 2015. The 12-ETF ERC sleeve
has ex-ante annualized volatility of 6.55%, with a maximum absolute risk-share
error below 2e-11. Under the configured caps, the 5% and 8% volatility
targets are reached. The 10% and 14% targets both result in 8.48% volatility.

### 8.1 Baselines

- Equal-weighted portfolio over the available universe.
- 60/40 benchmark.

### 8.2 Classical

At a completed month-end close, use 756 trailing sessions through that close.
The existing Step 2.3 shrinkage supplies annual arithmetic excess means.
Ledoit–Wolf constant-correlation covariance uses simple returns over the
same window. The risky sleeve is fully invested and long-only with the
configured 35% per-ETF cap.

For a positive feasible excess mean, minimize variance in rescaled weights
`y` subject to `mu @ y = 1` and `0 <= y_i <= cap * sum(y)`. Normalizing
`y` gives the maximum ex-ante Sharpe portfolio under the caps. If even the
highest feasible excess mean is nonpositive, use capped GMV and record
`gmv_nonpositive`. A solver failure raises an explicit error.

The Step 5.1 notebook checks 96 month-ends from January 2010 through
December 2017. All satisfy the caps and use tangency. On 31 December 2015,
the estimated annual volatility was 6.73% for Classic and 5.75% for capped
GMV. Their ex-ante Sharpe ratios were 0.975 and 0.717 under the same inputs.
Realized strategy performance is evaluated in Step 6.

### 8.3 Balanced

Fit the Ledoit–Wolf constant-correlation covariance on the configured 756
simple-return observations through the decision close. Solve the equal
risk-budget log-barrier problem and rescale the weights to sum to one.
Balanced uses covariance alone. Each ETF's share of volatility is 1 divided
by the number of eligible ETFs in the risky sleeve.

On the 96 monthly decisions from January 2010 through December 2017, the
12-ETF sleeve has a maximum absolute risk-share error below 9e-11. Its
estimated annual volatility on 31 December 2015 is 6.55%. The raw sleeve
exceeds the configured 35% per-ETF limit on 11 dates and reaches 36.03%
in IEF on 30 July 2010. Client-specific reoptimization belongs to Step
5.6b. Recalculate contributions after applying the client constraints.

### 8.4 Connected

Use the Step 5.2 ERC sleeve as the reference and the same annualized
covariance. The annual excess-mean prior is `(reference_sharpe / vol(x0))
* Sigma @ x0`, so the reference has the configured implied Sharpe of 0.35.
Inputs `Q` and `Omega` use the annual units described in Step 4.3.

When there are active views, fit a long-only tangency sleeve using the
posterior excess means and the same covariance. Start at the exploratory
upper value `tau = 0.05` with fixed `Omega`. If tracking error exceeds 3%
annualized, solve for a smaller `tau` that reaches the 3% boundary. Smaller
tilts can remain below 3%. Both settings are explicit inputs. Step 5.6b
handles client constraints on the resulting sleeve.

With zero active views, Connected returns the ERC weights and prior exactly.
The notebook verified this identity on 214 extended-sample month-ends from
30 January 2009 to 30 October 2026. With synthetic views, tracking error
is 0.15% in the weak-confidence case and 3.00% in the strong-confidence
case at calibrated `tau = 0.0153`. Activation of real views depends on
Step 4.6. Sensitivity to the anchor, `tau` and `Omega` is tracked in Step 5.9.

#### Chosen reference portfolio

DR-02 selects ERC because it distributes estimated volatility risk equally
among the eligible ETFs and requires no expected-return forecast. Under
equal positive individual Sharpe ratios and constant pairwise correlations,
the ERC and maximum-Sharpe portfolios coincide.
[Maillard, Roncalli & Teïletche, §3.5](https://doi.org/10.3905/jpm.2010.36.4.060).

For positive-definite `Sigma`, take `prior = s × Sigma @ x0 / vol(x0)`
with `s > 0`. The Sharpe of a candidate `w` under that prior is
`s × (w.T @ Sigma @ x0) / (vol(w) × vol(x0))`. By Cauchy–Schwarz it is
at most `s`, with equality when `w` is a positive multiple of `x0`.
Full investment then gives `w = x0`, provided the anchor is feasible.
This reverse-optimization result holds for any feasible anchor under its
own implied means. The 60/40 anchor is an alternative for Step 5.9.

Across 96 month-ends from January 2010 to December 2017, the ERC anchor's
implied Sharpe is 0.35. Solving the linear system for the anchor gives a
maximum absolute weight difference of 1.33e-15. The separate long-only
tangency optimizer recovers it within 4.14e-6 in weight units. The notebook
also records these checks. Realized returns are evaluated in Step 6.

#### Sensitivity to the reference and uncertainty

Step 5.9 uses 756-session windows ending 30 July 2010, 31 December 2015
and 29 December 2017. At each date, embed the 12-ETF ERC sleeve and the
60/40 SPY–IEF benchmark on the same 13-ETF Ledoit–Wolf covariance. Both
references use an implied Sharpe of 0.35. The only active test view is a
synthetic annual XLK minus XLE excess-return spread of 8%. The grid uses
`tau = 0.01, 0.025, 0.05` and `Omega` equal to 1, 2 or 4 times
`0.05 × P @ Sigma @ P.T`, which keeps view uncertainty fixed while
varying tau at each multiplier.

All 54 no-view cases preserve the anchor and its implied means. In the
54 active cases, fixed-tau tracking error ranges from 0.29% to 5.74%.
Three cases require smaller tau to meet the 3% ceiling. On 31 December
2015, with the ERC anchor and tau fixed at 0.05, raising the Omega
multiplier from 1 to 4 reduces the posterior spread from 3.55% to 0.87%.
At fixed Omega the posterior moves closer to the view as tau rises.
Scaling both tau and Omega by the same factor leaves the posterior
unchanged because the factors cancel in the Black–Litterman update.

The [experiment log](06_EXPERIMENT_LOG.md) records E023. This experiment
uses realized market covariances and synthetic views to check portfolio
mechanics. Step 4.6 remains the gate for real sentiment views.

#### No-view identity and confidence response

Step 5.13 runs the sentiment view matrix, spread calibration and
uncertainty estimate with zero eligible views. The posterior equals the
implied prior, and Connected has exactly the same ETF and cash weights
as Balanced in all four bands at both the 31 December 2015 and
30 October 2026 decision closes.

At the December 2015 close, vary the estimated uncertainty of the
same synthetic 8% annual XLK–XLE spread, holding the anchor and
`tau = 0.05` fixed. At four times, twice and once the uncertainty
floor, annualized tracking error to ERC is 1.40%, 1.93% and 2.51%.
The posterior spread rises from 0.87% to 3.55%. Cutting validation
error further leaves the floor binding and keeps the tilt at 2.51%.

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
switching. Revisit the labels and budget assumptions on the historical-vintage
fit before portfolio validation.

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

### 8.7 Chameleon exploratory allocations

The Step 5.4 experiment E022 uses the Step 4.4b state labels for this
specific exploratory fit. These group shares were set before the portfolio
run, using more bond and gold risk in stress and more equity risk in calm
expansion.

| Filtered regime | Equity | Bonds | Gold |
|---|---:|---:|---:|
| 0 — Expansion under financial strain | 45% | 40% | 15% |
| 1 — Low-inflation expansion | 60% | 30% | 10% |
| 2 — Contraction and financial stress | 30% | 45% | 25% |
| 3 — Calm expansion, flat curve | 70% | 20% | 10% |

At the decision close, use the latest available filtered probabilities.
Month-end macro observations become available at the next NYSE session.
Mix the rows by probability, then split each resulting group risk budget
equally across its ETFs. The portfolio uses the shared risk-budget solver
and the 756-session trailing covariance. The table describes shares of
portfolio risk. The resulting capital weights can differ materially.

The 24 exploratory decisions from 29 February 2016 to 31 January 2018
match their group budgets within a maximum absolute error of 1.42e-10. The
low-inflation state dominates each month and the largest change in a group
target is 0.0276 percentage points. The budget choices and portfolio value
require vintage-aware validation across different regimes before the
extension enters the catalogue.

### 8.8 Risk-band volatility targeting

Step 5.6a scales the fully invested risky sleeve by the band's reference
volatility divided by its ex-ante volatility. The default caps risky
exposure at 1×. The labelled leveraged variant uses the configured 1.5×
ceiling. The remaining weight goes to cash, which is negative when
borrowing. The function recalculates ex-ante volatility and reports any
amount by which it falls below the reference.

The notebook verifies 3,072 allocations across four strategies, four risk
bands, two leverage settings and 96 month-ends in 2010–2017. With leverage
allowed, the 14% reference is reached on 0 of 96 dates for Classic,
11 for Balanced and Connected, and 40 for 60/40. The scaling check uses
each strategy's risky sleeve before applying the personal constraints in
Step 5.6b. Step 6 will apply the borrowing cost in DR-03 and measure
realized volatility.

### 8.9 Client constraints

Resolve the questionnaire's exclusions, borrowing permission and ETF cap
before constructing an allocation. Remove excluded assets from the
eligible covariance and risky sleeve. A sector exclusion also removes SPY
from the personalized benchmark variant because the broad ETF can hold
that sector. Gold excludes GLD. Treasuries exclude IEF and TLT. The
historical 60/40 benchmark keeps its fixed mandate.

First optimize on the eligible assets. If the proposed allocation would
exceed the client's capital cap, use the proposed risky exposure to
translate that cap into a normalized sleeve cap, then re-optimize. Classic
uses tangency and the existing GMV fallback. Balanced uses the convex
log-barrier ERC objective with the sleeve cap. A binding cap can change
the risk shares. Connected rebuilds its constrained ERC anchor and drops
any view touching an excluded asset. Its no-view allocation equals
constrained Balanced. The benchmark variant preserves the relative mix of
its surviving legs. A strategy with no eligible ETF is unavailable.

Scale the resulting sleeve with cash, applying the capital cap and the
borrowing limit to the final weights. The effective risk target is the
smaller of the category reference and the client's capacity, when
provided. Report the achieved volatility and the shortfall from the
category reference. With few eligible ETFs, the final capital limits can
leave a substantial cash balance.

The notebook verifies 144 allocations across three market snapshots and
three constraint scenarios. On 31 December 2015, for an 8% effective
target with energy and gold excluded, a 25% ETF cap and no borrowing,
Classic achieves 7.19% estimated volatility. Balanced and Connected
achieve 6.81%. The eligible benchmark has 25% IEF and 75% cash.

### 8.10 Versioned prepared portfolio catalogue

Run `python -m src.portfolio_catalogue` or the independent Step 5.6c
notebook cell. The builder verifies the source hashes and uses the last NYSE
month-end with a subsequent session in the prepared extended calendar.
It writes `results/portfolio_catalogue.parquet` with one row per configured
risk band and core strategy. The schema version specifies the columns.
The catalogue version fingerprints the decision date, inputs and row
contents. Each row includes dated ETF and cash weights, the configured
comparison period, risk estimates and applied allocation limits.

The standard catalogue uses a 35% final weight cap per ETF, no exclusions
and no borrowing. It records the shortfall against the reference and
checks whether estimated volatility falls inside the requested band.
On 30 October 2026, 7 of 16 entries fall inside their bands and 6 reach
their reference volatility. The benchmark allocation in the catalogue
scales its 60/40 sleeve with cash and the standard cap.

The five historical client metrics are null and the backtest status is
`pending_backtest`. Step 6 fills these metrics from the matching
common-sample net-of-cost series before the catalogue is used to compare
performances. The allocation snapshot and the comparison dates are separate
fields.

### 8.11 Portfolio analytics

Catalogue schema v2 adds signed Euler volatility contributions and each
ETF's share of total risk. Use the same sleeve covariance as the allocation,
and include cash with zero estimated volatility. The contributions sum to
portfolio volatility. Relative shares are undefined when volatility is zero.
Concentration is the Herfindahl index of the risky weights normalized to sum
to one, excluding cash.

Ex-ante tracking error uses the active weights relative to the 60/40
catalogue allocation for the same band. Estimate a joint Ledoit–Wolf
covariance on the 13 ETFs over the same decision window so both portfolios'
holdings enter the active-risk calculation. The reference allocation can
fall below the band's target because it shares the standard constraints.

The realized information ratio uses daily strategy return minus benchmark
return on identical dates, annualized as `sqrt(252) * mean(active) /
std(active, ddof=1)`. It is undefined with zero active volatility.
Step 6 supplies the matched net returns. Until then the catalogue field
remains null.

### 8.12 Expected Shortfall and diversification (LN6)

Catalogue schema v3 applies the prepared portfolio's decision-close weights
to the trailing 756 observations of daily ETF returns. Cash carries a
zero shock in this risk diagnostic. Report Expected Shortfall at 95% as
the average signed loss over the worst 5% of the empirical distribution.
Use fractional mass at the boundary when 5% of the observations is not an
integer. The output is a daily decimal loss, with positive values indicating
losses. The Step 2.1 descriptive table retains its original signed-return
convention. Step 6 will apply the loss calculation to realized net returns.

Normalize risky weights to sum to one for Herfindahl and Shannon. Shannon
uses natural logarithms, and its exponential gives the effective number of
ETF holdings. The diversification ratio is the weighted sum of individual
volatilities divided by the sleeve volatility, both from the same covariance.
It is undefined for zero portfolio volatility.

The Step 5.10 notebook checks all 16 snapshots on the window from
26 October 2023 to 30 October 2026. Balanced in the 8% risk band has
a daily Expected Shortfall of 1.09% loss, a Herfindahl index of 0.110,
10.64 effective holdings and a diversification ratio of 1.751.

### 8.13 Displaying achieved volatility

Recompute estimated annual volatility on the final ETF weights and the
decision-close covariance, treating cash as having zero variance. Catalogue
schema v4 stores the signed gap from the category reference and indicates
whether the estimate is below, within or above the category range. The
Portfolio Menu reuses the catalogue decision date and verifies the local
input hashes, then re-optimizes with the profile's resolved exclusions,
ETF cap, capacity ceiling and borrowing permission.

The page shows the reference, final estimate, signed gap in percentage
points and position relative to the band. It shows borrowed cash when
used and marks a strategy unavailable if its eligible ETF universe is
empty. Estimated risk is displayed separately from realized volatility,
which awaits the backtest. Local market files and the prepared catalogue
are required for the personalized estimates.

The notebook verifies eight estimates on two profiles at the 30 October
2026 close. With borrowing allowed in the 14% band, the estimated
volatilities are 13.07% for Classic and 12.66% for Balanced and Connected.
All three reach the permitted 1.5× risky exposure. The standard ETF cap
limits the benchmark variant to 5.62% estimated volatility.

### 8.14 Constraint and solver audit

Step 5.12 verifies total capital, long-only ETF bounds, exclusions,
borrowing and optional caps on equity, bonds and gold. Class caps refer
to final portfolio capital. A zero cap excludes the class. A positive
cap can reduce risky exposure and add cash while preserving the
re-optimized sleeve proportions. Class caps are supplied explicitly
for scenarios that need them.

The notebook validates 96 allocations over three decision closes, two
constraint scenarios, four risk bands and four strategies. The unit
tests simulate failures in the Classic, ERC and GMV solvers and reject
an invalid solution even when the reported status indicates success.
The Portfolio Menu distinguishes optimizer failures from missing or
incompatible input data.

### 8.15 Turnover screening

Experiment E024 compares regular monthly Classic rebalancing with a single
5% no-trade threshold on two-way turnover. At each elapsed decision close,
measure turnover against the drifted holdings. The threshold still requires
a trade if the drifted weights would violate the ETF cap at that decision.
The initial position is the same across variants. Illustrative fees at 0,
10 and 25 basis points apply to traded weight after the decision-session
asset moves. This pilot uses the fully invested Classic sleeve.

On the reused exploratory 2016–2017 validation window, both variants make
23 trades and have annualized two-way turnover of 206.01%. The net annualized
return is identical at all tested fee levels, including 5.87% at 10 bps.
Regular monthly rebalancing remains the implementation choice. Step 6
will evaluate all strategies with the full cash and financing assumptions.

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
