# Sources for the seven registered studies

Version 1, 22 November 2026. The [series catalogue](series_catalogue_v1.csv) maps each study to its observed inputs, comparison rule and missing prerequisites. The [raw manifest](raw_manifest_v1.csv) identifies the exact bytes and record coverage used in this inventory. The studies and their decision calendars are defined in the [frozen protocol](../study_protocol.md).

## What each study can use

| Study | Required and retrieved | Limit on the conclusion |
|---|---|---|
| H01, covariance | SPY (US equities), IEF (Treasuries), GLD (gold), CHF per USD and event extracts. Compare risk forecasts on the same equal-weight sleeve. | Price histories use the adjustments available at retrieval. Verify actions, dates and executable prices before ranking portfolios. |
| H02, volatility | The same three holdings, currency and daily returns. The longer lookback requires 756 earlier sessions. | Derived volatility and covariance come from the eligible history. The fixed basket does not establish results for a worldwide opportunity set. |
| H03, bond forecasting | IEF, USD bill quote DTB3, 10y–2y spread and 262 snapshots each of CPI, unemployment and industrial production. | The three monthly predictors have dated vintages. The spread and bill files are latest exports. Date-only inputs use the following eligible session unless publication time is substantiated. |
| H04, equity forecasting | SPY, DTB3, term spread and BAA–Treasury spread. Compare against the expanding mean. | The optional valuation input lacks a dated numerator and denominator. USD cash returns need a bill-pricing and rollover convention. |
| H05, US stock ranking | Monthly and daily CRSP, annual Compustat, historical CCM, French factors, momentum and size breakpoints. The catalogue lists the observed vendor columns. | The filing/entry timestamps and as-reported accounts needed to reconstruct the historical information set are missing. Delisting conventions, eligible firm-months and links require the cleaning checks in 3.2. |
| H06, sentiment and Black–Litterman | AAPL and SPY form the no-view comparator. The course CSV has 43,966 rows across 19 tickers, 2011-01-03 to 2020-03-23. A separate laboratory table has 48,716 dated rows at the ticker-day grain, beginning 2010-01-04. The price supplement has 259 sessions and ends 2011-01-07. | File-level coverage supports investigating the 2010 warm-up. Check the ticker-level overlap and the source of each return before scoring. The prospective timestamped sentiment feed is missing. The company-to-sector extension has zero verified publication-date matches in the imported sector panel. |
| H07, monitoring | The same three ETFs and CHF exchange rate, a fixed monthly comparator and registered cost scenarios of 0, 10 and 25 bp per traded notional. | Drift and modeled fees can be studied historically. The pack lacks actual client tariffs, FX charges and timed fills. Historical stock bid/ask columns do not establish execution costs for these ETF orders. |

For an investable USD buy-and-hold reference the catalogue records IEF for H03 and SPY for H04/H05, over their observed fund history. H06 uses its registered AAPL/SPY anchor. H05 stock history before 2005 lacks that SPY export. The primary forecast and stock-ranking comparators remain as registered.

The USD studies use the quoted DTB3 discount-basis rate as their cash input. For the CHF studies the selected cash benchmark is the SARON accumulation index, or a reconstruction from authorised fixings under the SIX convention. That series is missing from the pack. A zero-remuneration CHF reserve is an explicit scenario assumption. EUR, GBP and other spending currencies supported in the intake need their own cash and FX inputs before comparable portfolio results can be shown. No broker interest rate is inferred from an index. [DTB3 series](https://fred.stlouisfed.org/series/DTB3) · [CHF per USD series](https://fred.stlouisfed.org/series/DEXSZUS) · [SIX reference rate methodology](https://www.six-group.com/dam/download/market-data/indices/swiss-reference-rates/six-methodology-swiss-reference-rates-rules-en.pdf)

The 13 ETF series include US-listed sector funds, two Treasury ETFs and a gold holding. Copper and oil spot observations in the pack can be predictors. A tradeable copper or oil allocation would require a specified security and a return history including its carry or roll. International equity markets, a historical universe of closed funds and additional local-currency holdings are outside the registered three-ETF comparison. Across 1,683 common daily CHF returns from January 2020 through October 2026, the daily standard deviation of an equal-weight series was 0.671% for the registered three ETFs and 0.994% for all 13. This descriptive sensitivity uses daily rebalanced weights, two adjacent ETF sessions with observed FX, and no costs. It measures the effect of changing this particular basket.

## Reading the raw manifest

The inventory covers observations and source archives under `data/raw`, `data/additional_data/raw` and the supplied course-data directory. It omits source-manifest files, generated tables, transport chunks and filesystem placeholders. SHA-256 is over the full stored bytes, including compressed containers. The earlier receipt check additionally verifies the decompressed ALFRED payloads against their imported checksums. Two course files each have an identical copy in a second location. Both paths are inventoried.

Each row has the source or surviving query description, retrieval time when documented, vintage, count basis, raw date range and missing-value convention or an explicit unresolved marker. Raw counts include missing values on the source grid. Catalogue coverage for a FRED series describes observed values. For CCM and GICS the manifest dates are interval starts. FOMC sentence labels are dated only to a year. The SIC dictionary has 49 explicit ranges and an implicit “Other” group. The original data-entry timestamp remains unknown for most sources. A recorded period end can be later than the audit date, as in the imported sector file. It never establishes availability at an earlier decision.

Of the 843 paths, 46 have a documented retrieval timestamp. For 786 ALFRED snapshots the vintage date and query survive, but the original download time is unknown. We preserve that distinction. A separate 3.1 notebook check compares each monthly vintage to the final archived snapshot. Backdating the final file would create 260 CPI, 261 industrial-production and 260 unemployment current-month observations unavailable in the corresponding historical snapshots. Studies using accounting data without historical entry or filing evidence remain restricted to exploratory work.

The catalogue lists observed coverage separately from the earliest supported decision use. A historical series can be useful for description while its first executable or publication-verified use remains unknown. Access terms are recorded conservatively from the import. Ownership of a file does not establish a right to display or redistribute the underlying vendor data.

## Reproduction

From the repository root, the two historical checks use the pinned packages in `requirements-data.txt`. A checkout that contains only the transport chunks needs the existing restoration command first. These operations require access to the research pack.

```sh
python research/restore_large_data.py
python research/verify_import.py
python research/audit_sources.py
```

The default audit reads all raw snapshots and compares their paths, hashes, counts, ranges and metadata with v1. A changed, missing or additional snapshot rejects the audit. Keep affected versions outside analytical use until the source and revision are reconciled. An intentional revision gets a separate path using `--create NEW_PATH`. Recheck that version with `--verify NEW_PATH`. Existing manifests are protected from overwrite.

For an entirely fictional, redistributable demonstration, only [the fixture](../../data/demo/source_events_v1.json) and [the standard-library checker](../check_source_fixture.py) are needed. The six independent expected rows cover a split, an unavailable close, CHF conversion, a dated macro revision, a cash delisting and two withdrawals. The negative case requests CHF 61 against CHF 60 settled cash. Its rejection is part of the check.

```sh
python -I -S research/check_source_fixture.py
```

After the two-for-one split, 4 units at USD 50 and CHF 0.90 per dollar plus CHF 60 cash still equal CHF 240. On the missing-close date, the CHF 20 withdrawal reduces cash to CHF 40 while wealth remains unvalued. The final CHF 219 includes the delisting proceeds and the final withdrawal. The synthetic CI job checks out these two files alongside the existing course examples, with no historical data or network dependency for running the ledger.
