# Data

This directory deliberately separates raw data from prepared data.

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
| `sentiment_firm_daily.parquet` | Professor-provided StockTwits data | Message day; usable from next business day |
| `sentiment_asset_daily.parquet` | Direct StockTwits tags for the 12 ETFs and SPY | Next business day; provisional MVP signal |

The notebook and application must load sentiment through
`src.data_loader.load_sentiment_firm_daily`, which adds `available_date` and
validates counts, duplicates, and polarity bounds.

Generate the provisional direct-ETF artifact with
`python -m src.build_sentiment_assets`. It deliberately does not infer company
sectors. Replace or supplement it only after a dated company-to-GICS mapping
has been reviewed and tested.

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

