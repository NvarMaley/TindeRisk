"""Download and materialize the reproducible Step 1 market-data bundle.

Run from the repository root:

    python -m src.build_market_data

Raw downloads are kept under ``data/raw`` for local provenance.  Cleaned,
aligned artifacts and their checksums are written under ``data/processed``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import yaml
import pandas as pd

from .data_loader import (
    MACRO_TRANSFORMS,
    MONTHLY_MACRO_SERIES,
    apply_publication_lag,
    clean_market_data,
    download_adjusted_prices,
    download_fred_series,
    transform_macro_series,
)
from .paths import PROCESSED_DATA, RAW_DATA, ROOT
from .provenance import observation_records, sha256_file


def _checksum(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    tickers = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    tickers.append(config["benchmark"])
    start = config["start_date"]
    rf_id = config["fred_series"]["risk_free"]
    macro_ids = config["fred_series"]["macro"]

    RAW_DATA.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA.mkdir(parents=True, exist_ok=True)

    print(f"Downloading adjusted prices for {len(tickers)} tickers...")
    prices_raw = download_adjusted_prices(tickers, start)
    prices_downloaded = datetime.now(UTC).isoformat(timespec="seconds")
    prices_raw.to_csv(RAW_DATA / "etf_prices_adjusted.csv")
    provenance = [
        observation_records(
            prices_raw[ticker].dropna(),
            available_dates=prices_raw[ticker].dropna().index,
            source="Yahoo Finance via yfinance; auto_adjust=True",
            downloaded_at_utc=prices_downloaded,
            availability_rule="observation-date close; not usable before close; current session may be provisional",
        ) for ticker in tickers
    ]
    downloads = {"prices": {"downloaded_at_utc": prices_downloaded,
                            "raw_sha256": sha256_file(RAW_DATA / "etf_prices_adjusted.csv")}}

    print(f"Downloading FRED {rf_id}...")
    rf_raw = download_fred_series(rf_id)
    rf_downloaded = datetime.now(UTC).isoformat(timespec="seconds")
    rf_raw.to_frame(rf_id).to_csv(RAW_DATA / f"{rf_id}.csv")
    provenance.append(observation_records(
        rf_raw.dropna(), available_dates=rf_raw.dropna().index,
        source=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={rf_id}",
        downloaded_at_utc=rf_downloaded,
        availability_rule="observation-date rate; publication time not verified; same-date use requires review before final backtest",
    ))
    downloads[rf_id] = {"downloaded_at_utc": rf_downloaded,
                        "raw_sha256": sha256_file(RAW_DATA / f"{rf_id}.csv")}

    macro_available = {}
    for series_id in macro_ids:
        print(f"Downloading FRED {series_id}...")
        raw = download_fred_series(series_id)
        downloaded = datetime.now(UTC).isoformat(timespec="seconds")
        raw.to_frame(series_id).to_csv(RAW_DATA / f"{series_id}.csv")
        transformed = transform_macro_series(raw, MACRO_TRANSFORMS[series_id])
        macro_available[series_id] = apply_publication_lag(
            transformed, monthly=series_id in MONTHLY_MACRO_SERIES
        )
        provenance.append(observation_records(
            transformed, available_dates=macro_available[series_id].index,
            source=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
            downloaded_at_utc=downloaded,
            availability_rule=("end of following month; latest vintage, not revision-safe"
                               if series_id in MONTHLY_MACRO_SERIES
                               else "next weekday; latest vintage; exchange alignment required at consumption"),
        ))
        downloads[series_id] = {"downloaded_at_utc": downloaded,
                                "raw_sha256": sha256_file(RAW_DATA / f"{series_id}.csv")}

    outputs = clean_market_data(prices_raw, rf_raw, macro_available)
    metadata = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "start": str(outputs["returns"].index.min().date()),
        "end": str(outputs["returns"].index.max().date()),
        "tickers": tickers,
        "sources": {
            "prices": "Yahoo Finance via yfinance, auto_adjust=True",
            "risk_free": f"FRED {rf_id}",
            "macro": [f"FRED {series_id}" for series_id in macro_ids],
        },
        "availability_rules": {
            "prices": "close of observation date",
            "risk_free": "last published observation forward-filled on trading days",
            "macro_daily": "next business day",
            "macro_monthly": "end of the month following the observation month",
        },
        "files": {},
        "downloads": downloads,
        "provenance_limitations": "Availability dates are modelling assumptions; FRED is latest-vintage, not point-in-time. DTB3 same-date timing requires review.",
    }

    for name, frame in outputs.items():
        path = PROCESSED_DATA / f"{name}.parquet"
        frame.to_parquet(path)
        metadata["files"][name] = {
            "file": path.name,
            "shape": list(frame.shape),
            "sha256": _checksum(path),
        }
        print(f"Saved {path.relative_to(ROOT)} {frame.shape}")

    provenance_path = PROCESSED_DATA / "market_observation_provenance.parquet"
    records = pd.concat(provenance, ignore_index=True)
    records.to_parquet(provenance_path, index=False)
    metadata["files"]["market_observation_provenance"] = {
        "file": provenance_path.name, "shape": list(records.shape),
        "sha256": sha256_file(provenance_path),
    }
    metadata_path = PROCESSED_DATA / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {metadata_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
