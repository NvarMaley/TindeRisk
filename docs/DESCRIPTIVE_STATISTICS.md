# Chapter 07 — Descriptive statistics

Run `python scripts/build_descriptive_panel.py` after chapter 6. The local data are exploratory research. Each asset is analyzed separately by source, frequency, return kind and currency. Price returns, reported total returns and conditional bond scenarios remain distinct. Irregular Treasury valuation intervals have no fixed annualization or serial-time assumption.

| Measure | Convention |
|---|---|
| Count and missingness | Count finite observations and explicit nulls; no replacement with zero |
| Quantiles | Linear empirical quantiles at 1, 5, 25, 50, 75, 95 and 99 percent, min and max |
| Mean and dispersion | Arithmetic, geometric, median; variance and standard deviation use n−1 |
| Volatility | Sample standard deviation × sqrt(K); K=252 exchange daily, 365 crypto daily, 52 weekly, 12 monthly |
| Downside deviation | Root mean square of min(r,0), using all valid observations |
| Skewness / kurtosis | Finite-sample adjusted Fisher skewness and excess kurtosis; null for insufficient or constant samples |
| Distribution | Histogram, empirical CDF evaluated at 49 quantile points, QQ against standard-normal quantiles, asymptotic Jarque–Bera p-value |
| Serial dependence | ACF, Yule–Walker PACF, Ljung–Box Q and chi-square p-value on the longest contiguous valid run, up to ten lags |
| Stationarity | ADF(1) with intercept, statistic only; nonstandard critical distribution, no unsupported conventional t-test p-value |
| Covariance | Exact common start/end intervals, sample denominator n−1; complete-case matrix whose symmetry and PSD are tested |
| Correlation | Pearson and average-rank Spearman; constant series have null correlation |
| Rolling estimates | 20 trailing consecutive periods, no incomplete window, annualized volatility and matched-benchmark beta/correlation when both series have full coverage |
| Cross-section | Percent rank within source/currency/kind and exact matching period; quantile clipping and standardization fit on observations through 2019-12-31, applied only after that date. Unavailable training histories produce null features. |

The Universe tab opens a searchable, paginated client catalogue displaying each instrument's name, ticker, source and profile button. Clicking the button navigates directly to a dedicated statistical profile, including an explicit unavailable-data state when needed. Acquisition and screening evidence remains in Sources. Each individual profile shows observed prices when available, returns, explanatory metric cards, quantile box plots, a histogram with a fitted normal reference, ECDF and QQ plots, serial diagnostics, rolling statistics, and cross-sectional features. The API permits one to eight assets from a common frequency, across different sources, over user-selected dates, UTC cutoff, currency and a common return kind. Matrices use exact common start/end intervals. Historical price series remain in their original USD source units; missing price, benchmark or training observations stay unavailable. Display labels from dated reference tables aid identification without conferring historical membership. The main Portfolios tab remains the simulation shortlist comparison. Published code contains no observations or instrument identities from licensed datasets. The G02 historical data approval gate remains required for subsequent real-data financial models; the synthetic and exploratory descriptive engine may be evaluated separately.

## Local validation

The corrected 2026-11-24 build covers 26 return-source/frequency groups and produced 27,230 statistical profiles, 2,093,782 rolling observations and 2,064,387 cross-sectional observations. It contains 1,649,925 valid rolling means and 1,195,183 matched-benchmark rolling betas. No standardized return is populated before the training cutoff.

| Covariance reference | Assets | Exact common intervals | PSD |
|---|---:|---:|---|
| CRSP ETF daily total returns | 27 | 1885 | yes |
| CRSP ETF monthly total returns | 27 | 90 | yes |
| Recent listed total returns | 27 | 223 | yes |
| Recent listed and crypto price returns | 29 | 177 | yes |

The cross-asset price matrix uses only exact intervals common to exchange and crypto calendars. It does not establish holding eligibility, cash-flow completeness or approved portfolio performance.
