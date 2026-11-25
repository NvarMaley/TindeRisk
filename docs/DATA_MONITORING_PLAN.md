# RiskMatch — complete research universe and ongoing data coverage

As of 2026-11-24. No new paid subscription or account has been created. All data remains local, and no allocation is approved.

Budget constraint: CHF 0 for data acquisition. FedInvest is an official no-cost source of dated security-level government valuation marks. Initial snapshots have been acquired from the public historical-prices form; the complete daily backfill is still pending. Run `python3 scripts/fetch_fedinvest_prices.py --start 2008-09-02 --end 2026-11-23 --limit 100` in batches (existing dated receipts are skipped). Respect access limits; do not equate the source's buy/sell or end-of-day prices with executable market quotes. Zero buy values are not usable quotations. FRNs are outside the current investment scope; validate maturity, coupon, TIPS ratios, accrued interest and historical identity separately. Coverage near redemption may be incomplete.

## Initial acquisition snapshot (superseded)

See [Source review and dictionary](SOURCE_REVIEW.md) and the chapter 3 checklist for the latest scope. Futures backfill is archived.

| Scope | Available now | Remaining |
|---|---|---|
| 22 ETF research candidates | CRSP daily and monthly histories through 2025, recent adjusted price histories for 12 | 2026 refresh for every ETF on one licensed feed; daily trading volume and price/return flags; reconcile source conventions and corporate actions |
| 1,000 stock research candidates | CRSP preliminary rank; 3,658 classified candidates, 1,000 selected at 2025-12-31, all observed that date | Refresh through 2026; time-varying historic membership, delisting, listings, REITs, liquidity and point-in-time qualification |
| 5 Treasury ETF current holdings | All 5 issuer snapshots downloaded; report dates 20/23 Nov 2026 | All report auxiliary money-market fund shares; strict direct-Treasury-only rule fails. Historical holdings and publication dates remain missing; no silent look-through or exception |
| Direct Treasury identities | 3,468 historical CUSIPs from verified auction receipts, 444 non-matured candidates at cutoff; FedInvest partial dated price observations | Complete FedInvest backfill and validation; verify outstanding status, buybacks/calls, executable secondary prices, accrued interest, coupon and TIPS index ratios; no auction-price substitute |
| Macro / cash / FX | 15 public latest-vintage FRED series; local ALFRED inputs | Complete PIT vintage and release timestamps, contractual USD/CHF funding conventions |
| Futures family identities | 10 roots, official CME specification references, no actual approved contract history | Contract-specific expiry, settlements, volume, open interest, multiplier, tick, margin and roll; specialist historical subscription |
| Fundamentals / factors | Local Compustat annual/CCM, factor archives | Quarterly statements, actual publication/revisions, refresh coverage and rights |

Public SEC N-PORT bulk archive is free but the 2026 Q3 ZIP alone is about 441 MB; bulk 2019–2026 would be many gigabytes for all US funds. Target five series rather than downloading every fund indiscriminately. The public filing-index examples and verified series identifiers are in `configs/sec_nport_targets.json`. SEC reporting period is distinct from acceptance date; no assumed access at period end. For scripted SEC acquisition, configure a real project contact in the declared User-Agent and respect [fair-access policy](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). Historical coverage before 2019 requires earlier filings or licensed CRSP mutual fund holdings. No fabricated daily positions.

## Treasury-only policy decision

The issuer snapshots for all five candidate funds include a money-market fund share. Under the current explicit rule (direct Treasuries plus incidental USD cash only), they are blocked. BlackRock's [September 2026 Treasury Fund SL Agency factsheet](https://www.blackrock.com/cash/literature/fact-sheet/bcf-treasury-fund-sl-agency-shares-factsheet.pdf) states its master portfolio can invest in Treasury-collateralized repos as well as direct Treasury debt and cash; a repo is not a direct Treasury debt holding. No inference is made from the product name. A possible future research rule is a separately authorized, verified look-through for ancillary Treasury-backed cash management, including an explicit decision on repo counterparty exposure, dated weights and holding caps. Until the owner approves a changed policy and evidence is verified, do not relax the rule. Direct Treasury candidates remain the alternative, subject to pricing validation.

## One provider versus a multi-source architecture

| Provider | Role | Coverage boundary |
|---|---|---|
| WRDS/CRSP/Compustat via HEC | Historical point-in-time research foundation and periodic updates | Institutional research entitlement, not a real-time production feed |
| [EODHD](https://eodhd.com/help/plans) | Low-cost EOD equity/ETF update candidate | Free plan advertises 20 calls/day and one year history; not enough for all 22 every day or 1,000 stocks. Adjusted close, OHLC and volume via official EOD endpoint; actual rights and quality need validation |
| [Databento](https://databento.com/pricing) | Exchange futures and equities candidate | Historical/live CME-family contract data and definitions under subscription; not a complete fundamentals/individual Treasury/ETF holdings source |
| [LSEG DataScope Select](https://www.lseg.com/en/data-analytics/products/datascope-select-data-delivery) | Institutional consolidated pricing/reference candidate | Broad equities, futures, funds, FX, rates and government debt; contract-level settlement, holdings, fundamentals, PIT vintages and API redistribution rights must be confirmed in the purchased entitlement. No free all-in-one guarantee |
| Bloomberg / FactSet | Alternative institutional procurement candidates | Confirm actual historical, API/bulk and non-display use entitlements with HEC or employer; no account assumed |
| FRED/ALFRED, Treasury Fiscal Data, SEC, issuers | Official macro, Treasury identity, filings and holdings supplements | Non-tradable reference data, publication delays and source-specific rights; not a unified live trading feed |

Recommendation: avoid vendor lock-in. For research use WRDS + official public sources; for ongoing market data evaluate an institutional cross-asset plan if available through HEC. Otherwise paid EOD equity feed plus a dedicated futures/individual-Treasury entitlement, with official filings/macroeconomic sources. Do not assume that buying a terminal also licenses automated data extraction or redistribution.

## Refresh architecture (not scheduled yet)

One adapter per source; immutable snapshots with receipt timestamp, source version, cutoff, SHA-256 and rights. For daily updates request data only after the relevant market session and provider publication, normalize UTC/local exchange times, compare with previous observations, quarantine missing/changed/duplicate/unreconciled rows. Reconcile corporate actions before stitching CRSP/alternate feed; retain both raw sources and record source-selection decision. No forward-filling price gaps. Cash/FX/curves have separate conventions. Fundamentals and holdings update on release/filing availability rather than a fictional daily schedule. Review source staleness before every model run and block orders when data are unavailable. No automated live execution.

Suggested frequency: EOD equities/ETF/futures prices and spreads daily; FX/rates daily; fundamentals and holdings on filing/publication (issuer current snapshot daily where permitted); macro on releases and vintage revisions; security master and futures specs on changes; factor series on producer publication. A future monitor should show expected timestamps and actual receipt, stale/missing status, source conflicts, license state and last successful refresh. A scheduled task or paid subscription requires owner authorization and appropriate credentials; none configured here.

## Minimum owner input still needed

1. For free price API trial, obtain an authorized EODHD token, set `EODHD_API_TOKEN` locally in the shell (do not paste into chat, commit or store in notebook). `scripts/fetch_eod_updates.py` already validates OHLC, adjusted close, volume and date range; limits requests to 20 or less and retains pending symbols. No token exists in the current environment. One-year free plan can test the 2026 gap in batches, but is not a sustainable daily feed for the complete universe.
2. On WRDS, check for the 2026 CRSP refresh and missing daily price/return flags. Volume, delistings, quarterly fundamentals and CCM link history have been delivered. Filing and revision chronology remains open. Check if CRSP fund holdings and contract-level futures are included. See [exact request checklist](DATA_ACQUISITION_PLAN.md).
3. For extra ALFRED vintage queries, obtain your own official FRED API key; no current key configured. For automated SEC queries declare an actual contact address (`SEC_CONTACT_EMAIL` in the shell). `scripts/fetch_sec_nport_samples.py` is prepared for five verified series/accession examples and correctly stops without a declared contact; the examples are not complete historical coverage.
4. Decide explicitly whether Treasury-backed money-market/repo look-through is within the chosen risk universe; current strict restriction stays in force.

Local commands added: `scripts/fetch_issuer_holdings.py`, `scripts/build_treasury_identity.py`, `scripts/audit_issuer_holdings.py`, `scripts/fetch_eod_updates.py`. The first three were executed and generated only ignored local artifacts. The EOD adapter correctly stops without credentials; no new live price observations are claimed. The full raw WRDS dataset and raw public downloads are not published to GitHub.

## November public-source refresh

Use a pinned whole-market snapshot and match historical identifiers offline. Preserve unmatched symbols for dated corporate-action review. The public exchange-bar refresh, issuer NAV workbooks and issuer reinvestment examples answer different questions. Record the latest market session and the number of sessions actually observed for each source.

Read SEC portfolio reports on their public filing dates. For financial statements preserve original accession, acceptance time, currency, taxonomy and reporting duration. FedInvest marks have their own publication calendar. Futures research files have a fixed historical cutoff. Refresh the source audit before interpreting the bilingual Sources view. See [verified acquisition coverage](DATA_ACQUISITION_PLAN.md).
