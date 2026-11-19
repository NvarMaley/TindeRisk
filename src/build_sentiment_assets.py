"""Build the lightweight direct-ETF sentiment artifact used by the MVP.

The full firm-level file contains thousands of tickers.  Until a dated,
reviewed company-to-GICS mapping is available, the reproducible MVP uses only
messages posted directly against the investable ETFs and SPY.  This avoids an
undocumented or look-ahead-prone company classification.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime

import yaml
import pandas as pd

from .data_loader import aggregate_sentiment_to_assets, load_sentiment_firm_daily
from .paths import PROCESSED_DATA, ROOT
from .provenance import sha256_file


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    sentiment_config = config["sentiment"]
    download_date = sentiment_config.get("original_download_date")
    download_month = sentiment_config.get("original_download_month")
    if download_month is not None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(download_month)):
        raise ValueError("StockTwits original_download_month must use YYYY-MM format")
    download_status = "reported_month_only" if download_month else "unknown_original_download"
    if download_date is not None:
        reported_date = str(download_date)
        try:
            download_date = date.fromisoformat(reported_date).isoformat()
            if download_date != reported_date:
                raise ValueError
        except ValueError as exc:
            raise ValueError("StockTwits original_download_date must use YYYY-MM-DD format") from exc
        download_month = download_date[:7]
        download_status = "reported_date"
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    benchmark = config["benchmark"]
    tickers = assets + [benchmark]
    mapping = {ticker: ("MARKET" if ticker == benchmark else ticker) for ticker in tickers}

    sentiment = load_sentiment_firm_daily(tickers=tickers)
    asset_daily = aggregate_sentiment_to_assets(sentiment, mapping)
    output = PROCESSED_DATA / "sentiment_asset_daily.parquet"
    asset_daily.to_parquet(output, index=False)
    provenance = asset_daily[["asset", "date", "available_date"]].rename(
        columns={"date": "observation_date"}
    ).copy()
    provenance["source"] = "Professor StockTwits; published firm-day counts; direct ETF tags"
    provenance["downloaded_at_utc"] = pd.NaT
    provenance["download_date"] = pd.Series(download_date, index=provenance.index, dtype="string")
    provenance["download_month"] = pd.Series(download_month, index=provenance.index, dtype="string")
    provenance["download_status"] = download_status
    provenance["availability_rule"] = "strictly next NYSE session; conservative daily assumption"
    provenance.to_parquet(PROCESSED_DATA / "sentiment_observation_provenance.parquet", index=False)

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
        "source_file": "sentiment_firm_daily.parquet",
        "source_sha256": sha256_file(PROCESSED_DATA / "sentiment_firm_daily.parquet"),
        "files": {
            name: {"sha256": sha256_file(PROCESSED_DATA / name)}
            for name in ["sentiment_asset_daily.parquet",
                         "sentiment_observation_provenance.parquet",
                         "sentiment_asset_coverage.csv"]
        },
        "downloaded_at_utc": None,
        "download_date": download_date,
        "download_month": download_month,
        "download_status": download_status,
    }
    (PROCESSED_DATA / "sentiment_asset_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved {output.relative_to(ROOT)} {asset_daily.shape}")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
