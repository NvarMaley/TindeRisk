"""Audit the local market bundle without modifying prices or deleting outliers.

Run ``python -m src.audit_data`` after building market data.
"""

import json

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .paths import PROCESSED_DATA, ROOT
from .data_loader import next_market_session, validate_sentiment_firm_daily
from .provenance import sha256_file


def audit_prices(prices: pd.DataFrame) -> dict:
    """Reject gaps, duplicate dates, non-session rows and invalid prices."""
    if prices.empty or len(prices) < 2 or not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("prices require a nonempty DatetimeIndex")
    if prices.index.hasnans or prices.index.tz is not None or not prices.index.equals(prices.index.normalize()):
        raise ValueError("price dates must be nonmissing normalized timezone-naive dates")
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise ValueError("price dates must be unique and sorted")
    if prices.columns.duplicated().any():
        raise ValueError("duplicate price columns")
    if not np.isfinite(prices.to_numpy(dtype=float)).all() or prices.le(0).any().any():
        raise ValueError("prices must be finite, positive and complete")
    sessions = mcal.get_calendar("NYSE").valid_days(
        prices.index.min(), prices.index.max(), tz=None
    )
    missing = sessions.difference(prices.index)
    unexpected = prices.index.difference(sessions)
    if len(missing) or len(unexpected):
        raise ValueError(f"calendar mismatch: missing={list(missing)}, unexpected={list(unexpected)}")
    returns = prices.pct_change(fill_method=None).iloc[1:]
    jumps = returns.stack()
    jumps = jumps[jumps.abs() > 0.25]
    return {
        "calendar": "NYSE",
        "rows": len(prices),
        "assets": len(prices.columns),
        "first_date": str(prices.index.min().date()),
        "last_date": str(prices.index.max().date()),
        "missing_sessions": 0,
        "unexpected_sessions": 0,
        "outlier_threshold": 0.25,
        "outliers_retained_for_review": [
            {"date": str(date.date()), "ticker": ticker, "return": float(value)}
            for (date, ticker), value in jumps.items()
        ],
    }


def audit_market_bundle(frames: dict, expected_tickers: list[str], macro_series: list[str]) -> dict:
    """Check schemas and arithmetic across every numerical market artifact."""
    required = {"prices", "returns", "log_returns", "rf_daily", "excess_returns", "macro"}
    if required - frames.keys():
        raise ValueError(f"missing market artifacts: {sorted(required - frames.keys())}")
    prices = frames["prices"]
    if list(prices.columns) != expected_tickers:
        raise ValueError("price schema differs from the configured universe")
    report = audit_prices(prices)
    expected_returns = prices.pct_change(fill_method=None).iloc[1:]
    returns = frames["returns"]
    pd.testing.assert_frame_equal(returns, expected_returns)
    pd.testing.assert_frame_equal(frames["log_returns"], np.log(prices).diff().iloc[1:])
    rf = frames["rf_daily"]
    if list(rf.columns) != ["rf_daily"]:
        raise ValueError("risk-free schema requires exactly rf_daily")
    if not rf.index.equals(returns.index) or not np.isfinite(rf.to_numpy()).all():
        raise ValueError("risk-free rate must be complete and aligned to returns")
    excess = frames["excess_returns"]
    pd.testing.assert_frame_equal(excess, returns.sub(rf["rf_daily"], axis=0))
    macro = frames["macro"]
    if list(macro.columns) != macro_series or not macro.index.equals(returns.index):
        raise ValueError("macro schema or calendar differs from configuration")
    if not np.isfinite(macro.to_numpy(dtype=float)).all():
        raise ValueError("macro values must be finite and complete over the market sample")
    report["returns_and_risk_free_alignment"] = "passed"
    report["log_returns_and_macro_schema"] = "passed"
    return report


def audit_asset_sentiment(frame: pd.DataFrame, expected_assets: list[str]) -> dict:
    """Verify chronology and report sparse observations without inventing zeros."""
    required = {"asset", "date", "available_date", "Nbullish", "Nbearish", "N", "polarity"}
    if required - set(frame.columns):
        raise ValueError("asset sentiment schema is incomplete")
    validate_sentiment_firm_daily(frame.rename(columns={"asset": "ticker"}))
    if frame.empty or set(frame["asset"].unique()) != set(expected_assets):
        raise ValueError("asset sentiment does not cover the configured assets")
    expected = next_market_session(frame["date"])
    if not pd.DatetimeIndex(frame["available_date"]).equals(expected):
        raise ValueError("sentiment availability differs from the strictly next NYSE session")
    coverage = {}
    for asset, group in frame.groupby("asset"):
        dates = pd.DatetimeIndex(group["date"])
        if not dates.is_monotonic_increasing:
            raise ValueError("sentiment dates must be sorted within each asset")
        sessions = mcal.get_calendar("NYSE").valid_days(dates.min(), dates.max(), tz=None)
        coverage[asset] = {
            "first_date": str(dates.min().date()), "last_date": str(dates.max().date()),
            "rows": len(group), "messages": int(group["N"].sum()),
            "sessions_without_observation": len(sessions.difference(dates)),
            "undefined_polarity_rows": int(group["polarity"].isna().sum()),
        }
    return {"coverage": coverage, "missing_observation_policy": "reported, not filled with zero or forward-filled"}


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    frames = {name: pd.read_parquet(PROCESSED_DATA / f"{name}.parquet")
              for name in ["prices", "returns", "log_returns", "rf_daily", "excess_returns", "macro"]}
    report = audit_market_bundle(frames, assets + [config["benchmark"]], config["fred_series"]["macro"])
    if frames["prices"].index.min() > pd.Timestamp(config["start_date"]) + pd.Timedelta(days=10):
        raise ValueError("prices do not cover the configured start")
    sentiment = pd.read_parquet(PROCESSED_DATA / "sentiment_asset_daily.parquet")
    report["sentiment"] = audit_asset_sentiment(sentiment, assets + ["MARKET"])
    metadata = json.loads((PROCESSED_DATA / "metadata.json").read_text())
    for info in metadata["files"].values():
        if sha256_file(PROCESSED_DATA / info["file"]) != info["sha256"]:
            raise ValueError(f"checksum mismatch: {info['file']}")
    sentiment_meta = json.loads((PROCESSED_DATA / "sentiment_asset_metadata.json").read_text())
    if sha256_file(PROCESSED_DATA / sentiment_meta["source_file"]) != sentiment_meta["source_sha256"]:
        raise ValueError("firm sentiment source checksum mismatch")
    report["checksums"] = "passed"
    report["scope"] = "market bundle and direct-ETF sentiment; company GICS, point-in-time certification and final sample selection remain open"
    (PROCESSED_DATA / "quality_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
