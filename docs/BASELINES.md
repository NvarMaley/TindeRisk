# Chapter 13 — Baseline portfolios

## Fixed reference definitions

| Reference | Funded weights | Rebalance variants |
|---|---|---|
| Cash proxy | 100% BIL | buy and hold |
| Equal weight | 20% each SPY, SHY, IEF, BIL, TIP | monthly, quarterly, buy and hold |
| 60/40 | 60% SPY, 40% IEF (intermediate US Treasury ETF) | monthly, quarterly, buy and hold |
| Market cap proxy | 100% SPY (US large-cap index ETF, not global market) | buy and hold |

All are long-only and fully funded. No optimizer or suitability claims. Use the same historical dates, currency, initial value 100 and cost model. Holdings include reinvested distributions via total returns. The strategy references are not the illustrative Chapter 12 goal mixes. The 575-asset Chapter 8 vector is additionally evaluated at 1/N weights with monthly, quarterly and buy-and-hold policies on its common sample; 549 stock and 26 ETF identities, static retrospective cohort with selection/survivorship bias. Compare against core cash, SPY and monthly 60/40 on exactly those dates, not against the longer core sample.

## Ledger and timing

Initial hypothetical buy at first interval start; mark holdings using the completed interval total returns; external cash flows enter at the interval end; monthly/quarterly target weights are chosen in advance and trades modeled at close marks. Quarter ends are March, June, September, December. No final unnecessary rebalance or liquidation. Buy-and-hold weights drift; if there is an external cash flow, invest or divest proportionally unless a rebalance is due. Costs are proportional per dollar of absolute traded notional, including purchase and sale legs and initial purchase. Exact self-financing equation: `V_after + c * sum(abs(w_target * V_after - h_before)) = V_before + flow`; solve monotone equation and verify reconciliation, no borrowing. Fee sensitivity at 0/5/10/25 bps, plus requested assumption. One-way turnover is half absolute traded notional divided by pretrade NAV; excludes initial trade in annual summary, includes any later flow trade. No taxes, spread/slippage beyond given fee; ETF operating expenses embedded in observed returns. Hypothetical close fills, not verified executable timestamps; final historical approval remains blocked.

Period time-weighted return removes external flow from end NAV and divides by prior period net NAV; first period starts with initial gross capital so initial fee counts. Cumulative compound index, CAGR (12 months per year), sample monthly volatility annualized, max drawdown, annualized mean monthly excess divided by standard deviation of excess, worst single month and rolling 12 months, monthly historical ES95 when at least 100 months. Historical stress periods are 2008, February–March 2020, and 2022 (only shown if all relevant months present). Separate illustrative instantaneous shock at ending weights: SPY -30%, SHY -3%, IEF -10%, BIL 0%, TIP -10%; not an estimate of maximum possible loss or verified client stress budget.

## Data and reproducibility

Source is verified local `etf_crsp_monthly`, exact shared start/end intervals with continuity, no imputation or source splicing. USD uses direct Fama-French monthly USD risk-free series from the same hashed PIT archive as return panel (rather than CPI-dependent join); original publication timestamps remain unverified. CHF returns are unhedged base-currency total returns, BIL CHF is a cash proxy and **not** CHF risk-free return. The ratio is explicitly labeled excess over cash proxy. Choose latest continuous matching segment; report all prior segments and missing-period breaks. As of 2026-11-25, USD 223 months May 31 2007 to Dec 31 2025; broad 575-asset cohort 100 months. CHF latest continuous core and cohort both cover 47 months, Jan 31 2022 to Dec 31 2025; core earlier segments contain 42 and 130 months. The universe is selected retrospectively; no out-of-sample optimization or PIT claims. Future optimizer must use the same ledger with dated, eligible weights, constraints and execution model. API `POST /api/baselines` accepts `as_of`, `currency`, optional `start`, `cost_bps`. Chapter 13 in the [research notebook](../notebooks/RiskMatch_V3.ipynb). No licensed data or computed results committed to GitHub.
