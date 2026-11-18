# Synthetic offline demonstration data

**SYNTHETIC DEMO ONLY. None of these values are historical market data.**

The small `market_bundle.json` fixture is generated entirely from a fixed seed
and local exchange-calendar rules. No Yahoo, FRED, StockTwits, WRDS, CRSP or
Compustat observations are read, sampled or embedded. ETF symbols and dates
are schema labels only. It can be shared with the project without redistributing
third-party source datasets; the project's separate code-license task remains
open.

## Contents and use

The bundle contains adjusted-price-shaped positive synthetic series for the
12 ETF labels and SPY, simple/log/excess returns, a synthetic cash proxy, six
fictional macro features, and synthetic message counts/polarities with explicit
missing observations and a zero-labelled example. A fabricated stress day
supports testing downside displays. Macro values are arbitrary features, not
realistic economic levels.

From the project root:

```python
from src.demo_data import load_demo

metadata, frames, sentiment = load_demo()
print(metadata["notice"])  # Always retain this label in any demo UI or export.
prices = frames["prices"]
returns = frames["returns"]
```

The file is committed, so loading it needs no network or source downloads.
Regenerate with `python -m src.demo_data`; verify with `python -m pytest -q`.
Loading is explicit: production functions never silently use this fixture.
Generated production artifacts in `data/processed/` are not overwritten.

## Limitations

- Not suitable for strategy ranking, model calibration, claims of historical
  performance or predictive validation.
- Too short for the production three-year estimation window. Tests of future
  backtest machinery may use a clearly labelled shorter fixture window, never
  silently change production configuration.
- Does not implement a questionnaire, portfolio catalogue or Streamlit demo.
  App wiring and visible demo labelling are tracked separately in 8.8/8.12.
- Does not resolve historical company-sector GICS data or unknown original
  StockTwits download timing.
