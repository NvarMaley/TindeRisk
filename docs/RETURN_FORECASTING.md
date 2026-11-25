# Chapter 08 — Experimental return forecasting

## Scope

One-period simple total or price return, in USD or CHF, at daily, weekly or
monthly frequency. The latest contiguous sequence of at most 2,500 intervals
from the verified return-source adapter is used. Missing intervals are never
compressed; a regular series with fewer than 100 observations is unavailable.
The result is research only, not a validated expected-return input.

## Design

For a label at interval t, features consist of the prior return, five- and
twenty-period means, twenty-period sample volatility and downside deviation.
One-step labels do not overlap. Split the examples chronologically 60/20/20;
fit only on train, select hyperparameters on validation; report the untouched
test. Causal rolling baselines update using only returns observed before each
forecast. No annualization or extrapolation of a one-period forecast.

Historical mean, rolling mean, EWMA (decay .94), zero-return reference; OLS,
Ridge, Lasso and Elastic Net (standardization fitted on train). Regularized
coefficients minimize mean squared loss / 2 plus alpha times the L1/L2 penalty.
Prespecified lag-only, shorter rolling-window and train-label clipping ablations. Random Forest,
XGBoost and MLP use pinned scikit-learn 1.6.1 and XGBoost 3.1.2 (CPU-only
distribution on Linux); deterministic seed 42, validation-only depth/width
selection, train-only target scaling. Non-converged MLP candidates are rejected.
The selected parameters record library versions. Missing packages are explicit.

## Evaluation and uncertainty

Consolidation: live monthly USD total-return profiles additionally expose a separately versioned cash reference. It verifies the upstream snapshot and Fama-French RF file hash, aligns unique continuous calendar months, uses the prior observation as a retrospective cash predictor and compares realized RF/excess returns on the same final test dates. The 223-month core run produced 41 test observations. Publication timing is unverified; daily, weekly, CHF and unsupported histories retain explicit missing cash coverage. Frozen universe forecast artifacts remain unchanged.

Validation residual 5th/95th quantiles give empirical 90% bounds, with no
coverage guarantee under distribution shift. Test MSE, MAE, directional
accuracy, temporal Spearman rank correlation (not cross-sectional IC), interval
coverage, test residual quantiles, gross buy-and-hold mean, and illustrative
long-or-cash mean net of 10 bps per unit turnover. The illustrative cash leg
earns zero; it is not the validated cash benchmark or executable backtest.
Select the candidate using minimum validation MSE, never test performance.

## References and outstanding gates

The synthetic factor reference fits CAPM and multifactor betas and uses
training factor means; the no-view Black–Litterman prior is delta times
covariance times market weights. Actual factor inputs, factor availability,
market covariance, cash benchmark and views require CH10/CH15/G02/G07.
Cross-sectional IC requires a contemporaneous eligible multi-asset panel.
Additional window ablations, extended OLS diagnostics and full economic backtests
remain pending. The advanced ML dependencies are installed by INSTALL.command
and CI from requirements-forecast.txt. The isolated macOS runtime successfully
fit all three models on synthetic data and on four local real-history assets
covering equity ETFs, a Treasury ETF, a commodity ETF and an individual stock.
The UI enables ML by default. Technical availability does not imply model
approval or closure of CH08.05/G07. Do not publish licensed series, predictions
or local data.

The asset profile exposes research forecasts, uncertainty and held-out
metrics. ForecastBundle carries version, provenance, one-period horizon,
currency, distribution reference and experimental status.

## Universe-wide batch

Run `.venv/bin/python scripts/build_forecast_universe.py --as-of 2026-11-24 --workers 4`.
Each catalogue item receives one outcome. In USD, prefer total return over
price return, then monthly, weekly and daily frequency; within a choice prefer
the latest available source. Require at least 100 contiguous intervals and
do not splice sources, fabricate missing history, or treat irregular returns
as regular. Every attempted source and reason is retained. Results and all
held-out predictions are stored in the ignored local forecasts directory,
with a content-hashed manifest, resumable checkpoint, and no Git data export.

The corrected 2026-11-24 run examined all 1,474 items: 1,008 computed all ten
core models plus references, 464 have separate conditional estimates and
two remain unavailable (one insufficient history, one absent series). No
fit errors. Of the computed assets, 580 monthly and 428 daily forecasts;
579 total-return and 429 price-return. Price/total simple forecasts and
intervals are bounded below by -100% before scoring and calibration; excess
returns have no such bound. Audit found no predictions below that bound.

The conditional estimates cover 391 nominal bills/notes/bonds, 53 TIPS,
19 short-history stocks and one cash reference. Bond yields use the latest
dated FedInvest marks (clean-price assumption), contractual maturity and
coupon, semiannual bond-equivalent yield for notes/bonds/TIPS and ACT/365
effective annual yield for bills. TIPS yield is real. Cash uses latest SOFR
as an indicative annualized overnight rate. Short histories use the arithmetic
mean of at least three valid observed intervals without filling gaps; no
out-of-sample validation or implied certainty. These are not comparable to
one-period expected returns. Two stocks have too little or no usable data.

A separate historical research vector includes 575 monthly USD total-return
forecasts with the same last observation date, 2025-12-31. This is not a current
or approved allocation input. No price-only returns, annual yields, mixed
frequencies or short-history estimates are silently converted to total returns.
The latest common-cutoff universe remains dependent on fresh and approved data.
The Sources page shows aggregate coverage;
the asset profile can load its saved universe forecast independently of
an on-demand calculation.

Run `.venv/bin/python scripts/audit_catalogue_coverage.py --as-of 2026-11-24`
to verify prior chapters against the distinct catalogue. Chapters 6 and 7
each have 1,473 assets with usable return/statistics profiles; one stock
has no usable series. The verified point-in-time snapshot has 61 partitions
and the return snapshot 30 partitions. These remain research artifacts.
