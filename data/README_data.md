# Data

This directory deliberately separates raw data from prepared data.

An additional [demo/](demo/README.md) directory contains a small committed,
fully synthetic offline fixture. Load it explicitly with
`from src.demo_data import load_demo`; it never replaces real market data or
supports investment-performance claims. Regenerate with
`python -m src.demo_data`. This fixture does not redistribute external-source
observations.

- `raw/`: files downloaded or provided by the professor. Never modify them.
- `processed/`: cleaned and aligned files, ready for the notebook and application.

For each new source, document the source, download date, covered period, and applied transformations in the pull request. Large files and files containing raw data are not version-controlled; other team members must be able to reproduce them from the notebook or a script in `src/`.

Planned sources: Yahoo Finance (`yfinance`), FRED, StockTwits course data, and FOMC documents. Check the licenses before publishing any data.

## Reproducible artifacts

Run `python -m src.build_market_data` from the repository root to download and
materialize the market bundle. The command writes adjusted prices, simple and
log returns, the daily risk-free rate, excess returns, macroeconomic variables,
and `metadata.json` with source and checksum information.

Run `python -m src.build_sentiment` only when the two professor-provided raw
StockTwits pickle files are available locally. The published
`processed/sentiment_firm_daily.parquet` is the reduced firm-day artifact; it
contains no message text or user identifiers.

| Artifact | Source | Coverage / availability rule |
|---|---|---|
| `prices.parquet` | Yahoo Finance adjusted close | Trading-day close |
| `returns.parquet`, `log_returns.parquet` | Derived from adjusted prices | No price filling |
| `rf_daily.parquet` | FRED DTB3 | Last observation forward-filled on trading days |
| `macro.parquet` | FRED series in `config.yaml` | Daily: next business day; monthly: end of following month |
| `sentiment_firm_daily.parquet` | Professor-provided StockTwits data | Message day; loader assigns the strictly next NYSE session |
| `sentiment_asset_daily.parquet` | Direct StockTwits tags for the 12 ETFs and SPY | Next NYSE session including holidays; provisional MVP signal |

The notebook and application must load sentiment through
`src.data_loader.load_sentiment_firm_daily`, which adds `available_date` and
validates counts, duplicates, and polarity bounds.

Generate the provisional direct-ETF artifact with
`python -m src.build_sentiment_assets`. It deliberately does not infer company
sectors. Replace or supplement it only after a dated company-to-GICS mapping
has been reviewed and tested.

The asset builder records SHA-256 hashes for its source, derived sentiment,
provenance sidecar and coverage CSV. Both `src.audit_data` and
`src.build_common_sample` verify these hashes before consuming sentiment.
An older metadata file without output hashes requires an explicit rerun of
`python -m src.build_sentiment_assets`. Hashes detect changes since generation;
they do not certify source accuracy or historical availability.

## LN7 lab reproduction

Run the two Step 4.1 cells of [RiskMatch_pipeline.ipynb](../RiskMatch_pipeline.ipynb).
The first cell reproduces the five SPY close-to-close returns shown in the
LN7 lab between 4 and 8 January 2010, at six decimals, using
`raw/etf_prices_adjusted.csv` from the Step 1 market-data build.

For the full run, place these original Moodle files under `data/raw/` and
load only copies from the instructor:

- `sentratio_and_price_closetoclose_adj2.pkl` supplies the ticker and SPY returns.
- `sentratio_and_price_for_pf2.pkl` supplies aligned message data, the market
  polarity benchmark and the instructor's event labels.

The lab's AR regression fits an intercept and SPY beta per ticker on
`(t − 365 days, t]`. For AP and AV, the reconstruction uses historical
observations strictly before each date and the instructor's aligned polarity,
market polarity and total message volume. The event rules use a rolling
sample standard deviation and the thresholds in the published methodology.
CAR and CAP sum residuals over complete windows of ±20 observed SPY sessions.
The second notebook cell compares reconstructed event counts and labels with
the Moodle data and reports how many complete event windows are available.
Exact event preprocessing and coverage remain to be checked on the original files.
[Divernois and Filipović, sections 4 and 6](https://doi.org/10.1007/s42521-023-00102-z).

The project's firm-day parquet is a calendar-day aggregate with a different
message count for AAPL on 4 January 2010 (24 versus 21 in the lab). The
reference for the Moodle run is 1,131 events (454 good, 294 neutral, 383 bad).

## LN7 historical company-to-sector links

The Step 4.1c notebook cell audits the 13 company symbols identified by the
lab, using observations in the project sentiment parquet between 4 January
2010 and 23 March 2020. The six fund symbols are outside the company link.
It links CRSP security-history tickers to PERMNO, then PERMNO to Compustat
GVKEY via the local CCM history. CCM uses primary links `P/C` and link types
`LC/LU/LS` following the WRDS example. Dates at either end of an interval
are inclusive. CCM end dates marked `E` represent open intervals. Missing
and conflicting mappings remain visible in the coverage counts. [WRDS CCM
example](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/wrds-macro-market-book-ratios-ciz/).

The local extracts lack historical GICS. Request the company-level **HGIC**
extract with GVKEY, sector code (`GSECTORH`) and effective start/end dates
(`INDFROM` and `INDTHRU`). Also obtain evidence of when the classification
was first available for use. Save the normalized export at
`data/raw/stocktwits_gics_history.csv` with the columns
`gvkey,gics_sector,effective_from,effective_through,known_from`.
Use ISO calendar dates and an empty end date for open intervals.
`known_from` means the first calendar date it was available for daily use.
Preserve leading zeroes in GVKEY. A row is eligible only when its sector
was effective and known on the observation date. [CCM HGIC data
guide](https://wrds-www.wharton.upenn.edu/documents/402/CRSP-Compustat_Merged_Database_Data_Guide_9efDcmD.pdf),
[S&P Global GICS History](https://www.marketplace.spglobal.com/en/datasets/gics-%2890%29).

## Company-derived sector sentiment

Step 4.1d tests a separate hypothesis from the LN7 company event study:
monthly polarity pooled across companies in a historical GICS sector could
relate to that sector's next-month return relative to the market. The notebook
calculates sector polarity and coverage. The comparison with forward returns and
its statistical validation are still pending.

For each eligible ticker-day, use the sector matched on the message date.
Sum bullish, bearish and total counts by sector, then calculate
`(bullish - bearish) / (bullish + bearish)` from the pooled counts.
The panels also report labelled counts and distinct GVKEYs. Days with ambiguous
or unavailable links contribute no counts. If a group has zero labelled
messages, its polarity stays undefined. Counts represent ticker mentions.

Monthly groups use the month of the next NYSE session after each message date.
The completed monthly signal is usable from the first NYSE session of the
following month. Keep incomplete months out of forward-return tests.
The notebook reports coverage on closed months and exposes a synthetic
month-end timing check that runs without the licensed inputs.

## Observation-level provenance (Step 1.8)

Source units, currency checks, adjusted-price evidence and DTB3 approximation
limits are documented in [Data Conventions](../docs/08_DATA_CONVENTIONS.md).
Reproduce the live vendor checks with `python -m src.check_conventions`.

The builders also produce numerical-input-independent provenance sidecars:

- `market_observation_provenance.parquet`: source-series observations (adjusted
  closes, nonmissing DTB3 observations and transformed macro values) with
  `observation_date`, modelled `available_date`, source URL/name, and the actual
  retrieval timestamp in UTC. Monthly transformations retain their original
  observation month separately from their lagged availability date.
- `sentiment_observation_provenance.parquet`: each direct-ETF asset/day and its
  next-NYSE-session availability. The original download timestamp is unknown:
  `downloaded_at_utc` remains null and `download_status` explains why. Ask the
  StockTwits data provider to supply the original retrieval date; do not replace
  it with a build time or filesystem modification time.
- `metadata.json`: per-source download timestamps and raw CSV SHA-256 hashes;
  provenance sidecar shape and hash. The sentiment metadata similarly records
  the input Parquet hash and distinguishes build time from download time.

These records cover source observations, not an expanded lineage row for every
forward-filled or derived return. The numerical files remain unchanged in
schema. Availability dates are explicit assumptions: latest-vintage FRED data
are not revision-safe, daily macro weekday lags need exchange alignment when
consumed, and DTB3 same-date usage requires a publication-timing review before
the final backtest. A date alone does not certify that a value was known at the
open. Prices are available at the close, not the start of the same day.

## Common comparison samples (Step 1.11)

Run `python -m src.build_common_sample` after both data builders. It retains
common complete market dates, excludes unclosed sessions, exports strictly
prior warm-up returns and aligns message counts on their availability sessions.
No missing sentiment is filled and no market dates are removed for missing
views. Periods, source coverage and input/output hashes are saved in
`common_sample_manifest.json`. See the
[common-sample specification](../docs/09_COMMON_SAMPLE.md) for filenames,
remaining GICS/cash-timing dependencies and signal-validation requirements.

## Market quality audit

Run `python -m src.audit_data` after building the market bundle. The audit
compares the price index with NYSE sessions, rejects missing sessions and
invalid/duplicate prices, verifies return arithmetic and risk-free alignment,
and writes `processed/quality_report.json`. Absolute daily moves above 25%
are reported for review, not clipped or deleted. A passing audit does not
certify the current session as final, historical FRED vintages, or company-sector
sentiment. Historical GICS remains an open dependency: see
[the checklist dependency gate](../CHECKLIST.md#gics-dependency) before
company-based sector aggregation or Black-Litterman views.

### Quality tests (Step 1.9)

`python -m pytest -q` tests corrupted numerical identities, schema mismatches,
missing configured assets, duplicate/unsorted dates, nonfinite prices and
counts, fractional counts, count/polarity consistency, calendar gaps, and
same-day sentiment leakage. Tests use small deterministic fixtures; the
published StockTwits artifact also has a direct-universe integration check.
Run `python -m src.audit_data` separately after generating the ignored market
files to validate all local numerical artifacts, macro coverage, input hashes,
and direct-ETF sentiment chronology.

The quality report lists sessions without a message-date observation per asset
between its first and last observations. Missing messages and zero labelled
messages are not assigned a neutral polarity. Because weekends can contribute
to the next session, this message-date metric is not the final usable-signal
coverage. Final alignment, minimum volume/confidence thresholds and permissible
signal age must be settled in checklist Steps 1.11, 4.3c and 4.6.

## Optional local research data (`data_plus/`)

`data_plus/` is intentionally ignored by Git because it is about 6.2 GB and
contains licensed WRDS/CRSP/Compustat extracts. It is not required for the MVP.
The useful components are limited to:

- Fama–French, momentum, q-factor, and BAB returns for later factor attribution
  and the alpha/beta robustness analysis in Step 6.8;
- CRSP ticker/SIC history as a local cross-check when constructing a dated
  company-to-sector mapping;
- prepared benchmark and transaction-cost series as methodological references.

Do not publish the WRDS, CRSP, or Compustat files. `USREC` and `GS10` are useful
only for the optional regime model, while `VIXCLS` duplicates a core FRED
download. The prepared portfolios named `S0`, etc. are unrelated to the four
RiskMatch strategies and must not be presented as RiskMatch results.

