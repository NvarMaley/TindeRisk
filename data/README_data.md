# Data inventory

- `raw/` holds market files, FRED series, StockTwits data, FOMC documents and local copies of `GICS.zip` and `sector.gz`.
- `processed/` holds prepared datasets and metadata.
- `demo/` holds the synthetic market bundle and the separate, dated CHF walkthrough derived from local historical inputs.
- `additional_data/` holds research inputs and their prepared versions.
- `Data for laboratories-20261119/` holds the datasets supplied for the labs.

Forecasting requires availability dates and a revision audit. ETF prices and the private WRDS panel cover different universes and periods. Check each study’s additional data requirements before use. [Research protocol](../RESEARCH.md)

## Public data for phase 2

The local `raw/public_phase2/` folder contains eight current-vintage FRED exports. DEXSZUS is CHF per USD. DGS2, DGS10 and DFII10 are interest rates in percent. T10YIE is breakeven inflation in percent. DTWEXBGS is the broad dollar index. DCOILWTICO is WTI in USD per barrel. PCOPPUSDM is copper in USD per metric ton. The JSON manifest records source URL, actual coverage and CSV checksum for each series. Dates without a quote remain missing.

In `alfred/`, 786 compressed snapshots cover CPIAUCSL, INDPRO and UNRATE at each of 262 month-end ETF sessions from January 2005 to October 2026. Each snapshot contains observations available in that ALFRED vintage, with history requested from 2000. The CSV manifest records URL, date and checksum of the decompressed contents. Vintages have daily resolution. Intraday decisions require the actual release time. Test the point-in-time joins before backtesting.

## Pilot data audit

Phase 2 data preparation runs `python -m research.data_collection` with authorized local inputs and prepared tables. It calls `data_audit.audit_local()` and writes the collection audit to `data/processed/collection_audit.json`. The checksums identify the inputs, including the optional WRDS panel and manifests. Document a new vintage and rerun the checks after an update. The checksum establishes which version was received. Historical availability requires separate evidence. [Pilot input checksums](pilot_checksums.json)

- **ETFs.** Reconcile both sample endpoints with the XNYS calendar. Check duplicates and finite positive prices. Compare returns recomputed without filling gaps against the prepared Parquet file. The provider adjusts the prices. An independent audit of dated dividends and splits remains open.
- **FRED and ALFRED.** Verify the eight checksums, reported gaps by series, date order, decompressed contents, observation dates and vintage sizes. Check actual release times for intraday forecasts. Dates in the market provenance file use assumed availability conventions.
- **FX.** Distinguish an observed quote, a valuation carried forward for up to three sessions, and a pair of consecutive quotes suitable for estimation. Exclude imputed returns from estimation. The pilot lacks 28 of 1,510 pairs. The selection error associated with those dates is unidentified.
- **StockTwits.** Check unique firm/date keys, bounded polarity, nonnegative message counts and a strictly later availability date for the prepared signal. Set polarity to missing when message volume is zero. Report attrition before and after each event window.
- **WRDS.** Check unique security/month keys, assumed availability dates and attrition. Compare book-to-market and return missingness by eligibility. H05 still requires replication from CRSP/Compustat, initial releases, delistings, inactive securities and cost tests.

A calendar-month-end check concealed 48,506 accounting availability dates later than the decision session, including 11,983 on rows marked investable. A further 122,861 rows had the same date without a timestamp. The H05 view masks accounting variables in both cases and retains securities and returns. An assumed date before the session does not establish actual publication.
