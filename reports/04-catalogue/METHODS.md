# Methods measured in the library 4

| Class and support | Calculation and unit | Perimeter or data to be obtained |
|---|---|---|
| US common stocks · CRSP | PERMNO identity at date, issuer and place classification, volumes and distributions reported, total local monthly return and in CHF. Four windows, risk of decline and dispersion. | End specific to the title, not more than December 2025. For daily checks and optimization over 504/756 sessions, get daily returns, dates, distributions, radiations and stable identifiers. |
| US share funds · SPY and nine sectors | Adjusted daily series, monthly measurements by fund, Pearson/Spearman and covariance in CHF. Weight of underlying holdings, issuers, sectors and currencies on published dates. | SPY sectors are assigned when an identifier returns to a single sector classification on the same day. Residual lines retained. Current positions do not rebuild an old composition. |
| Treasury Funds · IEF/TLT | Same sheets and correlations. Weight of identified US Treasuries and sum of declared weight × duration (years) in each fund. | Partial sensitivity of the documented investment sleeve. An estimate of convexity or a detailed curve shock requires flows and curves to date. |
| Direct US Treasury holdings | ISIN identifier, target price, coupon in%, maturity, duration published in the fund positions. | An observation does not estimate a total historical return, variance or maximum decline. Get full prices, coupons accrued and paid, dates and calendar, lots and executable quotes. |
| Gold · GLD | Priced vehicle return, volatility, correlations and decrease in CHF on the same windows as other funds. | Accurate composition on the date not validated. Avoid assigning an issuer to the full value. |
| WTI spot and US 10-year rate | FRED values and dates in USD/bar and% of nominal. Selection of available values at a date. | Series of factors. The spot can be negative and a rate change is measured in base points. For future investment, get the contract chain, rollover and collateral. |
| Macro, FX and cash CHF | ALFRED versions of three indicators, change CHF/USD and convert values. Reference cash rated at 0% under the assumption of 1.4. | Hours of first publication sometimes unknown. The net remuneration and availability of the client balance require the terms of the account. |
| Mixtures and comparison | Symmetric matrix on common dates, issuing attribution by weight of portfolio, root of variance available via covariance, 60/40 net according to 1.4. | Ranking of strategies, optimized weights and estimation of future returns at the next steps. The hypothetical costs of the comparison differ from a broker quote. |

## Read a sheet

The monthly arithmetic mean is multiplied by 12 for the annualized average. The variance of the decimal return sample is multiplied by 12, and its root gives annualized volatility. Total growth consists of local factors and changes to the boundaries. The CAGR is the final factor at power twelve divided by the number of months in the window, minus one. The rates published by the application are in percentage, the decimal variance squared. Monthly deviations can be time dependent. These are descriptive conventions of annualization.

The drawdown measures the loss from the previous highest level. A hollow shall be declared recovered only at the first observed recovery reaching the previous peak. The 95% historical Shortfall is the opposite of the average return at the bottom of the distribution, up to 5% empirical quantile, with tail strength. Asymmetry and excess Kurtosis are empirical moments. A single tail observation provides little precision. Covariance uses common months and the same change. The fund matrices include Pearson and Spearman, the large equity and fund matrix includes Pearson and covariance. [Calculation of forms](../../src/riskmatch_v2/library/statistics.py)

## Where to check local evidence

| Question | Product of the vintage |
|---|---|
| What instrument, what classification, what source, what date? | `instruments.parquet`, `identifiers.parquet`, `sources.parquet`, `schemas.json`, `manifest.json` |
| What session, what movement, what hole? | `prices.parquet`, `fx.parquet`, `events.parquet`, `dividend_audit.parquet`, `stock_months.parquet`, `stock_returns.parquet`, `stock_events.parquet`, `stock_quarantine.parquet` |
| What record or correlation? | `fund_sheets.parquet`, `stock_sheets.parquet`, `fonds_*a_*.parquet`, `covariance_coverage.parquet`, `universe_covariance.npz` |
| What would we have known or could have used? | `economic_calendar.parquet`, `macro_historique.parquet`, `macro_decision.parquet`, `replay_2025.parquet`, `decision.parquet` |
| What weight is held indirectly? | `holdings.parquet`, `concentration_*.parquet`, `fund_bond_sensitivity.parquet` |

The decision register applies a minimum of 36 months of risk and checks the freshness against the last closed session. Data on order, spread, lot, access to the account and actual charges are not included in this year. The minimum historical is a convention of the project. Macro factors, regime risk, sentiment, predictive econometric models and their possible weighting will be assessed over off-sample periods in sections 8 and 12. [Complete project directory](../../LIBRARY_METHODS.md) · [Catalogue rules](../../config/catalogue-4.json)

## Methods implemented on the complete universe

As of October 30, 2026, the multi-asset study submitted 3,322 securities, including 3,255 individual stocks, 54 direct Treasuries and 13 ETFs. Previous comparisons of 13 ETFs are used as a control. The catalogue measures returns in CHF, full prices and coupons for Treasury securities, and covariance between series on common dates. The border uses a factor model on the simultaneous universe. The replay holes retain a pattern. [Data and calculations](../univers-complet/README.md)
