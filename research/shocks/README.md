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
