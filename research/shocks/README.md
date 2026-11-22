# How the portfolios respond to market shocks

## Measurement protocol for section 4.2

The historical evaluation covers January 2020 through October 2026. Use the three USD funds and the CHF investor convention from 4.1. Compare the daily equal-weight SPY/IEF/GLD benchmark with an illustrative 60% SPY, 40% IEF mix on identical dates. Include CHF cash at par as a reference for instantaneous scenarios. Both invested mixes are unhedged, gross of trading and FX charges.

Use three simultaneous factors for local USD returns. The equity factor is SPY's own daily total return, so its equity coefficient is exactly one by construction. The other factors are one-session changes in the nominal US 10-year yield and 10-year breakeven inflation, expressed in decimal yield units. Higher breakeven with nominal yield fixed implies a lower approximate real yield. Breakeven also reflects risk and liquidity premia. The frozen inputs contain no dated duration, convexity, or cash-flow schedule for IEF. Its coefficient therefore measures empirical rate sensitivity conditional on equity and breakeven movements. USD/CHF reprices all USD holdings directly after the local shock. No FX regressor is used. [Nominal yield](https://fred.stlouisfed.org/series/DGS10) · [Breakeven definition](https://fred.stlouisfed.org/series/T10YIE)

At each month-end from December 2019 through October 2026, fit ordinary least squares with an intercept to the previous 252 exchange sessions, ending one venue session before month-end as an availability buffer. Require 200 jointly observed sessions and full rank. Use common dates for both allocations, with complete ETF returns, adjacent rate observations and adjacent FX marks. Show approximate 95% normal intervals using Bartlett HAC with five lags on the original session grid. The frozen retrospective snapshots lack verified historical arrival times. For the following month's historical attribution, combine that frozen fit with the subsequently observed factor movements and FX. Retain daily observed, explained and residual CHF returns. The intercept is included only for historical attribution. An isolated shock has zero intercept and zero idiosyncratic move by assumption.

Apply these instantaneous shocks at every cutoff. Units in the first and last columns are percent returns, and rate changes are basis points.

| Scenario | SPY | Nominal 10Y | Breakeven 10Y | CHF per USD |
|---|---:|---:|---:|---:|
| Equity fall | −10% | 0 | 0 | 0% |
| Nominal yield rise | 0% | +100 | 0 | 0% |
| Breakeven rise | 0% | 0 | +50 | 0% |
| USD depreciation | 0% | 0 | 0 | −5% |
| Joint shock | −10% | +100 | +50 | −5% |

Scale holding gains and losses by initial portfolio weights. Record the interaction of local repricing and FX explicitly and check totals against a direct revaluation of all positions. Shock sizes are illustrations. Large moves extrapolate local linear sensitivities, and joint moves need not have equal historical likelihood.

Classify each session using the previous venue close's VIX. Calm is at or below 20, stress at or above 30, and intermediate is between these cutoffs. Missing prior VIX gets its own group. Report scheduled and matched counts, mean and dispersion, and fitted exposures for supported groups. The thresholds are descriptive choices. They assign no trading positions or regime probabilities. [VIX definition](https://fred.stlouisfed.org/series/VIXCLS)

Select calendar windows before computing section 4.2 results, after the 4.1 historical review. Use 2020 Q1 (pandemic sell-off), calendar 2022 (inflation and tightening), and March 2023 (banking stress). These windows include quiet days and concurrent news. For each episode report actual compounded CHF portfolio performance from endpoint fixings and complete local paths, separately from matched daily model diagnostics. Refit the pooled episode sample omitting each episode in turn to test dependence on one event. Neither the group comparison nor the regression identifies an exogenous shock.

## Results

At the 30 October 2026 cutoff the fit uses 248 complete observations through 29 October. Each percentage below is a modeled change in CHF wealth at that cutoff. CHF cash at par has zero instantaneous nominal return in all five scenarios.

| Isolated or joint shock | Equal thirds | 60% equities, 40% Treasuries |
|---|---:|---:|
| Equities −10% | −5.89% | −6.02% |
| Nominal yield +100 bp | −4.32% | −2.84% |
| Breakeven +50 bp at fixed nominal yield | +1.14% | +0.10% |
| CHF per USD −5% | −5.00% | −5.00% |
| All four together | −13.62% | −13.31% |

For each CHF 100 in the equal-weight mix, SPY accounts for CHF 4.83 of the modeled joint loss, IEF for CHF 3.84 and GLD for CHF 4.94 before rounding. Local performance and FX multiply. Their interaction adds back 0.45 percentage points relative to simply adding the isolated shocks. The holdings sum to the independently revalued portfolio at every cutoff. No probability is assigned to these losses. [All scenarios](results/scenarios.csv) · [Holding and channel contributions](results/scenario_holdings.csv)

For IEF, a +100 bp nominal shock gives a modeled USD return of −7.10% at the final cutoff (approximate 95% coefficient interval −7.38% to −6.81%). Across the 83 monthly estimates the point response ranges from −8.19% to −7.08%. For gold, a +50 bp breakeven shock at the final cutoff gives +3.17% with an interval of −3.50% to +9.83%. That interval spans both losses and gains. It describes uncertainty about the fitted slope and excludes the day's unpredictable return. [Rolling coefficients and intervals](results/rolling_exposures.csv) · [Sensitivity chart](results/rolling_sensitivities.png)

| Historical episode | Sessions matched / scheduled | Equal thirds in CHF | 60/40 in CHF |
|---|---:|---:|---:|
| 2020 Q1 | 62 / 62 | −2.13% | −7.99% |
| 2022, available endpoint interval | 246 / 251 | −9.88% | −15.88% |
| March 2023 | 23 / 23 | +2.43% | +1.06% |

These are realized cumulative returns with daily USD rebalancing. The calendar-2022 opening FX mark (31 December 2021) is missing. The full-period field is empty. The supplemental result above uses the 3 January to 30 December 2022 observed closes, excluding the opening session's return. Matched daily counts refer to the scheduled windows. All episode and regime diagnostics compare the same dates for both allocations. [Exact valuation dates](results/episode_endpoints.csv) · [Observed, explained and residual daily results](results/historical_attribution.parquet)

In the 996 matched calm sessions, daily CHF volatility of the equal-weight mix was 0.54%, against 1.16% in 147 matched stress sessions. A further 540 sessions were intermediate and 34 of the 1,717 scheduled sessions lacked matched data. Daily residual root-mean-square error was 0.35% in calm markets and 0.46% in stressed markets. Market movements left material unexplained variation. Omitting each crisis in turn leaves IEF's modeled +100 bp response between −8.27% and −8.17%, compared with −8.30% in the pooled episodes. In March 2023 alone only 23 dates support the fit. Equity, rates, liquidity and FX moved together. These comparisons cannot establish which news caused a return or how often a shock will recur. [Regime and episode summaries](results/historical_summary.csv) · [Subsample estimates and intervals](results/subsample_exposures.csv)

## Reproduction

From the repository root with Python 3.12 and the frozen project data, run

```sh
python -m pip install -r requirements-descriptive.txt
python research/shocks/build.py
python tests/test_shocks.py
```

The builder verifies the prepared market and three raw input hashes. It checks the existing result directory against the new build. Use `--output /path/to/new-directory` to retain a separate result, including when rendering with a different graphics stack. The release contains 83 month-end fits and 82 months of subsequent daily attribution. CSV returns are decimal fractions. [Result hashes](results/manifest.json)
