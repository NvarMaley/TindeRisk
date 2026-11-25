# Chapter 06 — Returns and FX

The shared engine resides in `src/riskmatch/market_data/returns.py`. Run `python scripts/build_return_panel.py` after building the chapter 5 snapshot. All data remain local. The output is content-addressed by source snapshot and file hashes. Research calculations remain conditional on actual historical availability and source validation; they are not approved for portfolio backtesting.

| Method | Convention |
|---|---|
| Price return | P1/P0 - 1, in decimal units |
| Log return | log(1+r) only if r > -1 |
| Total return | (split × P1 + distribution per original share)/P0 - 1; never add a distribution to a vendor total-return series |
| Compounding | product(1+r) - 1; missing sessions invalidate the full period |
| Arithmetic / geometric | sum(r)/n; product(1+r)^(1/n)-1. Annualized geometric applies K = 252 trading days, 365 crypto days, 52 weeks or 12 months. Calendar CAGR uses the actual elapsed days. Research statistical means do not imply expected future returns. |
| FX | (1+rUSD) × CHF-per-USD at end / CHF-per-USD at start - 1; reciprocal convention tested; no FX forward fill |
| Real return | (1+r nominal)/(1+inflation)-1 using matching period CPI; latest-vintage USD ex-post research only |
| Cash accrual | simple rate × actual elapsed days / 360 or 365; SOFR percentage converted to decimal; separate index-implied benchmark |
| Excess return | asset return minus risk-free return at equal frequency |
| Nominal bond | (clean ending price + ending accrued + actual cash paid)/(clean starting price + starting accrued)-1 |
| TIPS | apply dated index ratios to real clean price and accrued interest; add actual USD cash payment |
| Futures | contracts × multiplier × (ending settlement - starting settlement); no log return or price denominator, including nonpositive settlements |
| TWR | compound subperiod returns using valuations after dated flows and subtract end-of-period external flows |
| MWR | dated annual XIRR with ACT/365, conventional cash-flow signs; reject ambiguous multiple-sign sequences |

## Real local research data

- CRSP ETF daily and monthly reported total returns remain separate from recent vendor research returns. The daily-to-monthly reconciliation uses exact matching endpoints. Recent listed product returns preserve missing event coverage. The 27 listed candidates include commodity ETPs; no derivative expiry series is activated.
- Historic stock cohort outcomes remain separate from 2026 ticker-based price references. Crypto spot has price return and CHF conversion where both endpoint FX rates exist. No staking, margin, futures roll, transaction fees or dividends are invented for price-only sources.
- Corporate-action correction: CRSP monthly price return uses reported ex-distribution return; daily ETF price return applies dated CRSP split/share-dividend factors (one plus the distribution price factor), quarantining ambiguous nonstandard factors or large disagreement with reported total return. Public closes are adjusted on a known single split only if the factor reduces the discontinuity; otherwise retain an apparently already-adjusted move if plausible. Unverified moves above 50% in absolute value and ambiguous events are unavailable, not winsorized or assigned fabricated returns. Public adjustment completeness remains provisional. The two audited ETF reverse-split spikes now reconcile to their reported returns.
- Equity and crypto calendars differ; frequency aggregation requires the recorded expected sessions. No incomplete terminal period is declared complete. Arithmetic and geometric statistics use observed rows; annualization and realized CAGR require continuous history covering approximately one year.
- FedInvest marks are valuation-only. The nominal bond scenario explicitly assumes clean marks and contractual cash paid. Actual cash-flow evidence and clean/dirty convention must be confirmed before realized total return; TIPS formula is tested on synthetic examples, while actual TIPS mark returns remain price-only. Futures are archived and the actual settlement ledger remains chapter 22.
- The monthly USD ex-post real and risk-free comparison uses CPI and Fama-French monthly RF. CHF real returns require Swiss inflation data. The cash index and ACT/360 comparison uses the same actual start/end dates.
- NAV TWR and date-based XIRR are tested on synthetic valuations; actual portfolio ledger reconciliation belongs to BT00 and chapter 23.

The local Web App Sources view shows return coverage, currency, frequency, units and method. Missing and unapproved totals must not be substituted with zero. Chapter 6 technical prerequisites can be validated independently of the later bond/futures trading ledger. The original G02 approval gate and later extended-ledger gates still apply.

## Local build evidence

The 2026-11-24 build retained 1,746,497 rows across 30 tables, including 360,774 monthly real/excess-return reference rows and 7,230 statistical summaries. All 7,344 comparable CRSP monthly intervals reconcile within 1e-5 decimal return (maximum absolute difference 5.73e-6); 3,961 also meet 1e-6. All 2,157 matched SOFR intervals reconcile within 1e-6 (maximum difference below 1e-8). Repeating the build produced the same content hash. These are source and interval comparisons, not investment eligibility or out-of-sample validation.
