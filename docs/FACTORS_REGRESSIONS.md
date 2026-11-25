# Chapter 10 — Factors and regressions

Research only. All asset rows, scores, portfolio observations and matrices
remain in ignored local files. The published factor history is a dated,
latest-vintage research source; actual publication availability, licensing,
execution and historical membership approval remain G07/G02 prerequisites.

## Thirteen-factor taxonomy

| Identity | Implemented research measurement | Limit |
|---|---|---|
| Market | Published Mkt-RF; CAPM and beta | Retrospective factor observations |
| Value | Published HML; dated SEC equity divided by original cap units, ranked | Ratio ranks, not verified absolute book-to-market units |
| Size | Published SMB; negative log dated market cap | SMB is five-factor definition |
| Momentum | Published Mom; 12-1 trailing contiguous monthly returns | Missing histories unavailable |
| Quality | Original annual SEC income/assets minus liabilities/assets | Partial profitability/leverage proxy |
| Low volatility | Negative trailing 12-month sample volatility | Requires contiguous observations |
| Profitability | Published RMW; dated SEC net income/equity proxy | Internal proxy not operating-profit RMW |
| Investment | Published CMA; negative year-over-year SEC asset growth | Require comparable annual fiscal dates |
| Carry | Change in 3-month Treasury yield; conditional YTM/SOFR reference | Not a traded carry/roll premium |
| Term | Change in 10-year Treasury yield; conditional duration | Not a term-premium portfolio |
| Treasury curve | Change in 10Y-2Y slope and 2*5Y-2Y-10Y curvature | Not executable key-rate hedges |
| Liquidity | Size-neutralized log reported monthly share volume | Not bid-ask spread or Amihud |
| Inflation | Ex-post monthly CPI change | Not an inflation surprise; consensus absent |

## Dated cross-sectional scores

Use dated membership and next-month outcomes. Trailing momentum excludes
the latest return, low-volatility uses twelve returns ending at ranking date.
Use only annual SEC filings accepted on a date strictly before the ranking
date, linked by unique eligible dated CCM identity. Conflicting facts do
not create a numeric score; stale filings are restricted to a three-year
search window. Investment uses successive fiscal dates 9–15 months apart.
Winsorize 1%/99% and standardize within each ranking cross-section; no
future cross-sectional observations. Liquidity is residualized on size.
No sector neutralization is asserted without approved classification.

Research portfolios use equal-weight top/bottom quintiles, at least 50
scored assets. Any missing selected outcome invalidates that period's
return. Record score coverage, rank IC on observed pairs, weight L1
turnover and illustrative 10 bps per unit turnover. No assumed borrow
availability/fees, actual after-close execution, or trading suitability.
Common last-20% test grid is selected from ranking-date availability;
net performance uses only the same complete-return periods across all
eight portfolios. No strategy selection using held-out results.

## Regressions and attribution

USD total-return excess targets are preferred. Price-only targets are
explicitly labelled and not interchangeable with total-return CAPM.
Monthly factors align by calendar month; daily equity factors use exact
end dates; crypto daily calendar returns are excluded. Matched observations
can contain gaps; HAC lags count observations rather than calendar days.
The monthly rolling beta requires consecutive months. Data are retrospective,
not a point-in-time predictive dataset.

CAPM, FF3 subset of FF5, FF5, FF5+Momentum, macro sensitivities and
internal style regressions fit OLS and train-only standardized ridge.
60/20/20 chronological split; ridge penalty selected on validation.
Report HAC errors, p-values, VIF, condition number, residual Durbin–Watson,
rolling beta and drift, conditional realized-factor MSE/MAE, and exact
held-out attribution alpha + beta'f + residual. The implied return
reference uses training factor means and RF, without alpha; it is not
a contemporaneous forecast or investment recommendation.

PCA uses training correlation with largest absolute loading positive and
held-out absolute loading similarity. For the exact Chapter 8/9 575-asset
cohort, estimate B Sigma_f B' on training excess returns with diagonal
and full residual covariance, preserving all factor cross-covariances.
Compare fixed equal-weight realized excess risk on test and report PSD
and condition number. The full residual matrix is singular; the diagonal
matrix is ill-conditioned. No approved allocation covariance or assumption
that excess and total-return covariances are interchangeable.

## Local evidence (2026-11-25)

Run `.venv/bin/python scripts/build_factor_universe.py --as-of 2026-11-25 --workers 4`.
1,474 items examined: 1,022 regressions (862 monthly total, 160 price-only);
445 analytical references (444 Treasury conditional duration/yield, one
SOFR); seven stocks unavailable. 5,725 regression specifications reconciled
attribution to within 1e-10. CAPM and FF3 subset cover 1,022, FF5 1,014,
FF6 993, macro 828, internal styles 846. The 336,000-row score panel has
eight score methods and 2,064 portfolio-period records. Common test has
36 ranking dates, 29 complete-return periods across all eight portfolios.
The 575-asset factor covariance has 99 exact common intervals at
2025-12-31 and passes both PSD checks. G07 and true carry, term premium,
inflation surprise, execution/borrow and validation remain open.
