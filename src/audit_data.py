"""Audit the local market bundle without modifying prices or deleting outliers.

Run ``python -m src.audit_data`` after building market data.
"""

import json

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from .paths import PROCESSED_DATA


def audit_prices(prices: pd.DataFrame) -> dict:
    """Reject gaps, duplicate dates, non-session rows and invalid prices."""
    if prices.empty or not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("prices require a nonempty DatetimeIndex")
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


def main() -> None:
    prices = pd.read_parquet(PROCESSED_DATA / "prices.parquet")
    report = audit_prices(prices)
    expected_returns = prices.pct_change(fill_method=None).iloc[1:]
    returns = pd.read_parquet(PROCESSED_DATA / "returns.parquet")
    pd.testing.assert_frame_equal(returns, expected_returns)
    rf = pd.read_parquet(PROCESSED_DATA / "rf_daily.parquet")
    if not rf.index.equals(returns.index) or not np.isfinite(rf.to_numpy()).all():
        raise ValueError("risk-free rate must be complete and aligned to returns")
    excess = pd.read_parquet(PROCESSED_DATA / "excess_returns.parquet")
    pd.testing.assert_frame_equal(excess, returns.sub(rf["rf_daily"], axis=0))
    report["returns_and_risk_free_alignment"] = "passed"
    report["scope"] = "market bundle only; firm-to-GICS mapping and signal validation remain open"
    (PROCESSED_DATA / "quality_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
