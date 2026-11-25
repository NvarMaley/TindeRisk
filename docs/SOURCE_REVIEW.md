# Source quality and method review

Reviewed 2026-11-24. The 16 logical datasets and their provider, identifiers, required fields, frequency and revision rules are in [the source catalog](../configs/source_catalog.json). A dataset may combine multiple physical sources. The local inventory groups files by acquisition feed. A group count is distinct from a dataset count.

The owner clarified that RiskMatch is a private university-course application and WRDS extracts were supplied through UNIL. Technical research preparation can proceed in this scope; specific data-use and historical approval checks remain documented.

## Field dictionary and method decisions

| Catalog dataset | Fields and units to check | Current research use and remaining condition |
|---|---|---|
| ETF_DAILY | Dated PERMNO, trading session, USD close, shares traded, total return in decimal, distribution flag | All 27 listed products passed the December 2025 closing-price bridge. A matching close cannot establish a total return. Check events and provider conventions. |
| ETF_MONTHLY | PERMNO, month end, total and ex-distribution returns, exit flags | Historical comparisons within covered CRSP months. Missing exit returns stay missing. |
| EQUITY_MASTER | PERMNO, valid dates, security classification, dated market cap and subsequent return | Historical rankings available. Retain 191 missing subsequent returns among 335,000 ranked observations as explicit gaps. |
| ETF_HOLDINGS | Fund and position identifier, portfolio date, filing acceptance timestamp, weight and weight unit | Use accepted filings from their availability time. Treasury-only tests require a complete attributable holdings snapshot. |
| FUNDAMENTALS | GVKEY, fiscal date, currency, units, accession and publication time | A fiscal date alone cannot support a historical signal. Use the original filing and its release time. |
| LINKS | GVKEY, PERMNO, link type, primary flag, validity interval | Resolve identities on the observation date. Ambiguous links require review. |
| TREASURY_MASTER | CUSIP, security type, issue and maturity dates, stated rate, dated coupon schedule | Nominal contractual schedules exist for 1,283 issues. Verify outstanding status on each decision date. |
| TREASURY_DAILY | CUSIP, mark date, price per 100, clean/dirty convention, accrued interest, coupon cash flow, TIPS index ratio | 2,690 issues have marks. Marks support valuation research. A holding-period return needs consistently accrued prices and actual cash flows, including indexation when applicable. |
| RATES_FX | Series ID, date, rate in percent or FX quote direction, release time | Use the documented units; yields require a separate holding-period return calculation. |
| MACRO_VINTAGES | Series, observation period, vintage, release timestamp, unit | Use only vintages available at decision time. Hold historical signals with uncertain release time. |
| FACTORS | Factor name, market, frequency, return scale, vintage | Confirm percent versus decimal, calendar and producer permission before comparison. |
| BENCHMARKS | Index ID, currency, return variant, observation date, membership dates and weights | A dated list supports membership checks. Benchmark replication also requires weights and corporate actions. |
| FUTURES | Dated contract ID, expiry, settlement, multiplier, tick, margin and roll convention | Archived outside the active chapter 3 universe. |
| COSTS_LIQUIDITY | Session, USD price, volume in shares, spread, effective fee dates | Dollar turnover is a liquidity proxy. Executable costs require spread and fee evidence. |
| SENTIMENT | Source, publication timestamp, vintage, scoring definition | Optional and held pending data rights and historical availability. |
| CRYPTO_SPOT | Market pair, UTC candle start, open/high/low/close in USD, volume in base units | BTC/USD and ETH/USD are research series. Preserve missing UTC days; review custody, fees and display permissions. |

## Rights and release decisions

| Source | Local storage and transformation | Collaboration and display |
|---|---|---|
| WRDS, CRSP, Compustat and CCM | Verify the institution's product-specific agreement for local copies, retention and derived research. Existing receipts establish provenance only. Further acquisition and use pending confirmation. | Hold collaborator access, exports and derived results for external testers until the institution confirms the permitted scope. [WRDS terms](https://wrds-www.wharton.upenn.edu/pages/about/data-download-and-analysis-policy/) |
| Treasury Fiscal Data and official valuation releases | Record the originating dataset, terms, units and snapshot separately. Treasury auction records and FedInvest marks serve different methods. | Project publishes code and synthetic fixtures. Check each originating service before releasing observations. [Fiscal Data](https://fiscaldata.treasury.gov/api-documentation/) |
| FRED, ALFRED, factors and index providers | Check the original provider and series-specific notices for storage and derived use. | Hold redistribution pending provider-specific review. [FRED terms](https://fred.stlouisfed.org/legal/) |
| SEC filings, fund issuers and public mirrors | Record filing/accession, original provider and retrieval separately. Review third-party content and mirror provenance individually. | Hold republication of third-party content. [SEC access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) |
| Coinbase market data | Restrict to internal research subject to applicable terms. | Hold external delivery of market data and derived outputs without appropriate permission. [Market data terms](https://www.coinbase.com/legal/market-data-terms) |

## Reproducible inventory

Run `python scripts/build_source_inventory.py` in the private project after staging the local acquisitions and WRDS delivery manifest. It fingerprints local bytes, records a path-and-content ingestion ID, and atomically publishes the DuckDB metadata catalog. Re-running retains the first verified UTC time. For old imports this time is the earliest verified local inventory timestamp. Original publication, actual download and first inventory verification are separate events. A historical receipt documents a version even if the original file subsequently moves.

Use `request_snapshot(ProviderRequest(provider, full_sha256, as_of))` for local exact-version metadata. Unknown versions and missing inventories produce explicit diagnostics. The web view exposes inventory counts. Populated databases, observation files and Parquet partitions stay in ignored data directories. Chapter 5 owns normalization. For a clean clone, run the synthetic tests and the notebook without institutional data.

The shared downloader uses a 30-second timeout, a 20 MB response cap and at most three attempts. It retries transient failures, defers longer server-directed waits to a later run and publishes complete files by content hash. A missing response stays missing. Adapters with other access policies use their own documented limits. Code, synthetic examples and aggregate readiness checks are the public deliverables.
