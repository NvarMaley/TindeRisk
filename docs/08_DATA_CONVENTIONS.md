# Data conventions — Step 1.10

## Prices, returns, currency and calendar

The configured 12 ETFs plus SPY are checked against Yahoo history metadata for
USD quote currency and `America/New_York` exchange timezone. This is the quote
currency, not a promise that the underlying exposures have no currency risk.
There is no CHF conversion or currency hedge.

The download uses `auto_adjust=True`; its Close is an adjusted price series,
not the nominal cash price at which historical trades could be executed.
Ratios are used as the vendor's dividend/split-adjusted return proxy. Do not
add dividends a second time. It is not an independently certified total-return
index; vendor revisions and adjustment errors remain possible. A 2019 sample
is cross-checked against Yahoo `Adj Close` downloaded with `auto_adjust=False`.
Returns are compared rather than levels, which later distributions can rescale.
See [yfinance history documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html).

Dates label daily exchange sessions; a normalized date is not a midnight
availability timestamp. Prices are known at the close. The NYSE calendar audit
checks holidays and missing sessions. Intraday/provisional latest prices must
not enter a frozen historical evaluation as final daily closes.

| Quantity | Convention |
|---|---|
| Simple asset return | `P[t] / P[t-1] - 1`, decimal; 0.01 means 1% |
| Log return | `log(P[t]) - log(P[t-1])`, statistical use; do not weight as simple portfolio returns |
| Excess return | Simple return minus the same-period daily risk-free proxy |
| Annualized arithmetic mean | Daily mean × 252; not compounded CAGR |
| Annualized volatility | Daily standard deviation × square root of 252 |
| Annualized covariance | Daily covariance × 252; variance, not volatility |
| Basis points | 10 bps = 0.001; 100 bps = 0.01 |

## Risk-free proxy: explicit approximation

[DTB3](https://fred.stlouisfed.org/series/DTB3) is an annual **bank-discount rate
quoted in percent**, not an investment-basis return. The current project
convention `DTB3 / 100 / 252` is retained and explicitly labelled as a daily
cash-rate **proxy**. For a 5% quote, it yields approximately 0.000198413 per
trading session. It is not an exact holding-period return on a three-month bill.
It does not model the bill's maturity-specific discount price or calendar-day
interest accrual (weekends included).

Before implementing cash accrual and financing in **6.1/6.3**, resolve the
publication-time assumption and select/document the accrual convention. Do not
claim that same-date DTB3 was available at the beginning of that session. This
verification does not silently change the team's cash-return methodology.
Latest-vintage downloads also do not certify point-in-time historical data.

## Macro source units and transformations

| Source | Raw units and frequency | Prepared value |
|---|---|---|
| [T10Y2Y](https://fred.stlouisfed.org/series/T10Y2Y) | Yield spread quoted in percent, daily | Unscaled level: numerical percentage-point spread, not decimal return |
| [BAA10Y](https://fred.stlouisfed.org/series/BAA10Y) | Yield spread quoted in percent, daily | Unscaled percentage-point spread |
| [VIXCLS](https://fred.stlouisfed.org/series/VIXCLS) | Index, daily close, not seasonally adjusted | Natural logarithm of index level; not a realized asset return |
| [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) | CPI index, monthly, seasonally adjusted | 12-month percentage change as a decimal |
| [UNRATE](https://fred.stlouisfed.org/series/UNRATE) | Percent, monthly, seasonally adjusted | 12-month difference in percentage points; 5 to 6 gives 1, not 0.01 |
| [INDPRO](https://fred.stlouisfed.org/series/INDPRO) | Industrial production index, monthly, seasonally adjusted | 12-month percentage change as a decimal |

Index base years can be rebased by providers; year-over-year ratios do not
depend on a constant rebase. Monthly lags are conservative modelled dates,
not actual vintage/release reconstruction. Units differ across macro columns;
fit standardization only on past training observations if implementing HMM.

## StockTwits

Counts are nonnegative integer message counts. `N` includes messages not
labelled bullish/bearish. Polarity is `(Nbullish - Nbearish) / (Nbullish +
Nbearish)`, dimensionless in [-1, 1]. A zero denominator produces missing
polarity, not neutral sentiment. It is not a percentage asset return. The
message date is a UTC daily bucket; exact intraday alignment cannot be recovered
from the aggregate. Availability is conservatively the following NYSE session.
Missing message-date observations are reported, not zero-filled. Company-based
sector aggregation still requires the [historical GICS gate](../CHECKLIST.md#gics-dependency).

## Reproduce the checks

- `python -m src.check_conventions`: live vendor currency/timezone and adjusted
  price checks; local DTB3 arithmetic; writes ignored
  `data/processed/conventions_report.json` with verification time and limitations.
- `python -m src.audit_data`: full local bundle calendar and arithmetic audit.
- `python -m pytest -q`: deterministic convention and quality regression tests.
