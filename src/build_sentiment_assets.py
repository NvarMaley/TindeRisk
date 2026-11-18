"""Build the lightweight direct-ETF sentiment artifact used by the MVP.

The full firm-level file contains thousands of tickers.  Until a dated,
reviewed company-to-GICS mapping is available, the reproducible MVP uses only
messages posted directly against the investable ETFs and SPY.  This avoids an
undocumented or look-ahead-prone company classification.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import yaml

from .data_loader import aggregate_sentiment_to_assets, load_sentiment_firm_daily
from .paths import PROCESSED_DATA, ROOT


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    benchmark = config["benchmark"]
    tickers = assets + [benchmark]
    mapping = {ticker: ("MARKET" if ticker == benchmark else ticker) for ticker in tickers}

    sentiment = load_sentiment_firm_daily(tickers=tickers)
    asset_daily = aggregate_sentiment_to_assets(sentiment, mapping)
    output = PROCESSED_DATA / "sentiment_asset_daily.parquet"
    asset_daily.to_parquet(output, index=False)

    coverage = (
        asset_daily.groupby("asset", observed=True)
        .agg(
            first_date=("date", "min"),
            last_date=("date", "max"),
            rows=("date", "size"),
            messages=("N", "sum"),
        )
        .reset_index()
    )
    coverage.to_csv(PROCESSED_DATA / "sentiment_asset_coverage.csv", index=False)
    metadata = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "method": "direct ETF and SPY StockTwits tags only",
        "anti_look_ahead": "available_date is the strictly next NYSE session after message date, including exchange holidays",
        "mapped_tickers": mapping,
        "company_to_gics_status": "pending a dated and reviewed mapping",
    }
    (PROCESSED_DATA / "sentiment_asset_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved {output.relative_to(ROOT)} {asset_daily.shape}")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
