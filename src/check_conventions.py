"""Verify price/currency conventions against Yahoo and local numerical inputs.

Run ``python -m src.check_conventions``; network access is explicit here.
"""

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import yaml

from .paths import PROCESSED_DATA, RAW_DATA, ROOT


def validate_quote_metadata(metadata: dict, expected_currency: str) -> dict:
    if metadata.get("currency") != expected_currency:
        raise ValueError(f"quote currency mismatch or missing: {metadata.get('currency')}")
    timezone = metadata.get("exchangeTimezoneName")
    if timezone != "America/New_York":
        raise ValueError(f"unexpected or missing exchange timezone: {timezone}")
    return {"currency": metadata["currency"], "timezone": timezone,
            "exchange": metadata.get("exchangeName", metadata.get("fullExchangeName"))}


def verify_adjusted_returns(prices: pd.DataFrame, adjusted: pd.DataFrame) -> None:
    """Compare returns, not absolute levels that future distributions rescale."""
    if list(prices.columns) != list(adjusted.columns) or not prices.index.equals(adjusted.index):
        raise ValueError("adjustment comparison requires matching dates and tickers")
    if prices.isna().any().any() or adjusted.isna().any().any() or len(prices) < 2:
        raise ValueError("adjustment comparison requires complete observations")
    np.testing.assert_allclose(
        prices.pct_change(fill_method=None).iloc[1:],
        adjusted.pct_change(fill_method=None).iloc[1:], rtol=1e-3, atol=1e-5,
    )


def main() -> None:
    import yfinance as yf

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    prices = pd.read_parquet(PROCESSED_DATA / "prices.parquet")
    tickers = list(prices.columns)
    report = {"checked_at_utc": datetime.now(UTC).isoformat(), "quotes": {}}
    for ticker in tickers:
        print(f"Checking quote currency/timezone: {ticker}", flush=True)
        report["quotes"][ticker] = validate_quote_metadata(
            yf.Ticker(ticker).get_history_metadata(), config["currency"]
        )
    raw = yf.download(tickers, start="2019-01-01", end="2020-01-01",
                      auto_adjust=False, progress=False, group_by="column")
    adjusted = raw["Adj Close"].loc[:, tickers].copy()
    adjusted.index = pd.DatetimeIndex(adjusted.index).tz_localize(None)
    verify_adjusted_returns(prices.loc[adjusted.index, tickers], adjusted)
    report["adjustment_cross_check"] = {
        "reference": "Yahoo Adj Close with auto_adjust=False",
        "sample": "2019 calendar year", "sessions": len(adjusted),
        "comparison": "simple returns; rtol=0.001, atol=0.00001",
        "status": "passed; vendor cross-check, not independent total-return certification",
    }
    rf_raw = pd.read_csv(RAW_DATA / "DTB3.csv", index_col=0, parse_dates=True)["DTB3"]
    rf = pd.read_parquet(PROCESSED_DATA / "rf_daily.parquet")["rf_daily"]
    expected = (rf_raw / 100 / 252).reindex(rf_raw.index.union(rf.index)).ffill().reindex(rf.index)
    np.testing.assert_allclose(rf.to_numpy(), expected.to_numpy())
    report["risk_free"] = {
        "source": "https://fred.stlouisfed.org/series/DTB3",
        "quoted_units": "annual bank-discount rate in percent",
        "model_units": "daily decimal proxy = quote / 100 / 252",
        "status": "arithmetic verified; approximation, not an exact T-bill holding-period return",
        "limits": "No maturity-specific discount-price conversion or calendar-day accrual; publication timing still requires review before backtesting.",
    }
    report["annualization"] = {"sessions_per_year": 252,
                               "arithmetic_mean": "daily mean * 252 (not CAGR)",
                               "volatility": "daily standard deviation * sqrt(252)",
                               "covariance": "daily covariance * 252"}
    report["calendar"] = "NYSE sessions; daily close labels, not midnight availability"
    report["currency"] = "USD quote currency; no CHF hedge or currency conversion"
    (PROCESSED_DATA / "conventions_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print("Conventions verified; wrote data/processed/conventions_report.json")


if __name__ == "__main__":
    main()
