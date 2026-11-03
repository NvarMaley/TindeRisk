# Data

This directory deliberately separates raw data from prepared data.

- `raw/`: files downloaded or provided by the professor. Never modify them.
- `processed/`: cleaned and aligned files, ready for the notebook and application.

For each new source, document the source, download date, covered period, and applied transformations in the pull request. Large files and files containing raw data are not version-controlled; other team members must be able to reproduce them from the notebook or a script in `src/`.

Planned sources: Yahoo Finance (`yfinance`), FRED, StockTwits course data, and FOMC documents. Check the licenses before publishing any data.

