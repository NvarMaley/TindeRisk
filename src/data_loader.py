"""Load, validate, and align the market inputs used by RiskMatch.

Network access is confined to the two download helpers.  The remaining
functions are deterministic so the notebook, tests, and application share the
same chronology and anti-look-ahead rules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import PROCESSED_DATA


SENTIMENT_COLUMNS = ("ticker", "date", "Nbullish", "Nbearish", "N", "polarity")
MONTHLY_MACRO_SERIES = frozenset({"CPIAUCSL", "UNRATE", "INDPRO"})
MACRO_TRANSFORMS = {
    "T10Y2Y": "level",
    "BAA10Y": "level",
    "VIXCLS": "log",
    "CPIAUCSL": "yoy",
    "UNRATE": "diff12",
    "INDPRO": "yoy",
}


def next_market_session(dates: pd.Series | pd.Index) -> pd.DatetimeIndex:
    """Return the strictly following NYSE session, including holiday closures."""
    import pandas_market_calendars as mcal

    observations = _normalise_datetime(dates)
    if observations.empty:
        return observations
    if observations.isna().any():
        raise ValueError("observation dates must not contain NaT")
    sessions = mcal.get_calendar("NYSE").valid_days(
        observations.min(), observations.max() + pd.Timedelta(days=31), tz=None
    )
    positions = sessions.searchsorted(observations, side="right")
    if (positions >= len(sessions)).any():
        raise ValueError("calendar does not cover the next market session")
    return sessions.take(positions)


def _normalise_datetime(values: pd.Series | pd.Index) -> pd.DatetimeIndex:
    """Return timezone-naive, normalized dates without changing chronology."""
    dates = pd.DatetimeIndex(pd.to_datetime(values, utc=True))
    return dates.tz_convert(None).normalize()


def validate_sentiment_firm_daily(frame: pd.DataFrame) -> None:
    """Validate the contract of the published firm-day sentiment artifact."""
    missing = [column for column in SENTIMENT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"sentiment data missing columns: {missing}")
    if frame[["ticker", "date", "Nbullish", "Nbearish", "N"]].isna().any().any():
        raise ValueError("sentiment identifiers and counts must not contain nulls")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("sentiment data contains duplicate ticker/date rows")

    counts = frame[["Nbullish", "Nbearish", "N"]]
    if (counts < 0).any().any():
        raise ValueError("sentiment counts must be non-negative")
    if (frame["Nbullish"] + frame["Nbearish"] > frame["N"]).any():
        raise ValueError("bullish plus bearish counts cannot exceed total messages")
    if frame["polarity"].dropna().abs().gt(1).any():
        raise ValueError("sentiment polarity must be in [-1, 1]")


def load_sentiment_firm_daily(
    path: str | Path = PROCESSED_DATA / "sentiment_firm_daily.parquet",
    *,
    tickers: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Load firm-day sentiment and add its first safe trading-use date.

    StockTwits messages observed on calendar day ``t`` are treated as known
    only after that day's close, so ``available_date`` is the strictly next
    NYSE session (including holidays). Passing ``tickers`` uses Parquet
    predicate pushdown and avoids loading
    the full multi-million-row dataset when only the investable ETFs are needed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"sentiment artifact not found: {path}")

    filters = [("ticker", "in", list(tickers))] if tickers else None
    frame = pd.read_parquet(path, filters=filters, columns=list(SENTIMENT_COLUMNS))
    frame = frame.copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["date"] = _normalise_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"], ignore_index=True)
    validate_sentiment_firm_daily(frame)
    frame["available_date"] = next_market_session(frame["date"])
    return frame


def aggregate_sentiment_to_assets(
    sentiment: pd.DataFrame,
    ticker_to_asset: Mapping[str, str],
) -> pd.DataFrame:
    """Aggregate mapped firm counts into point-in-time asset-level sentiment."""
    required = set(SENTIMENT_COLUMNS) | {"available_date"}
    missing = sorted(required - set(sentiment.columns))
    if missing:
        raise ValueError(f"sentiment data missing columns: {missing}")
    if not ticker_to_asset:
        raise ValueError("ticker_to_asset must not be empty")

    mapped = sentiment[sentiment["ticker"].isin(ticker_to_asset)].copy()
    if mapped.empty:
        raise ValueError("none of the mapped tickers occur in the sentiment data")
    mapped["asset"] = mapped["ticker"].map(ticker_to_asset)
    grouped = (
        mapped.groupby(["asset", "date", "available_date"], as_index=False, observed=True)
        [["Nbullish", "Nbearish", "N"]]
        .sum()
    )
    labelled = grouped["Nbullish"] + grouped["Nbearish"]
    grouped["polarity"] = (
        (grouped["Nbullish"] - grouped["Nbearish"]) / labelled.replace(0, np.nan)
    )
    return grouped.sort_values(["asset", "date"], ignore_index=True)


def download_adjusted_prices(
    tickers: Sequence[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Download dividend-adjusted close prices from Yahoo Finance."""
    if not tickers or len(set(tickers)) != len(tickers):
        raise ValueError("tickers must be a non-empty unique sequence")
    import yfinance as yf

    raw = yf.download(
        list(tickers),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )
    if raw.empty or "Close" not in raw:
        raise RuntimeError("Yahoo Finance returned no adjusted close prices")
    close = raw["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    missing = [ticker for ticker in tickers if ticker not in close or close[ticker].isna().all()]
    if missing:
        raise RuntimeError(f"Yahoo Finance returned no prices for: {missing}")
    close = close.loc[:, list(tickers)].copy()
    close.index = _normalise_datetime(close.index)
    close.index.name = "date"
    return close.sort_index()


def download_fred_series(series_id: str) -> pd.Series:
    """Download one FRED series from its stable CSV endpoint."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    frame = pd.read_csv(url, index_col=0, parse_dates=True, na_values=".")
    if series_id not in frame or frame[series_id].dropna().empty:
        raise RuntimeError(f"FRED returned no observations for {series_id}")
    series = frame[series_id].astype(float).sort_index()
    series.index = _normalise_datetime(series.index)
    series.index.name = "observation_date"
    return series


def transform_macro_series(series: pd.Series, how: str) -> pd.Series:
    """Apply the prespecified macroeconomic transformation on observation dates."""
    if how == "level":
        result = series
    elif how == "log":
        if series.dropna().le(0).any():
            raise ValueError("log transformation requires strictly positive observations")
        result = np.log(series)
    elif how == "yoy":
        result = series.pct_change(12, fill_method=None)
    elif how == "diff12":
        result = series.diff(12)
    else:
        raise ValueError(f"unknown macro transformation: {how}")
    return result.dropna()


def apply_publication_lag(series: pd.Series, *, monthly: bool) -> pd.Series:
    """Index a series by the conservative date on which it becomes usable."""
    result = series.copy()
    offset = pd.offsets.MonthEnd(2) if monthly else pd.offsets.BDay(1)
    result.index = pd.DatetimeIndex(result.index) + offset
    result.index.name = "available_date"
    return result


def clean_market_data(
    prices_raw: pd.DataFrame,
    rf_annual_percent: pd.Series,
    macro_available: Mapping[str, pd.Series] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build a complete common trading calendar without filling asset prices."""
    prices = prices_raw.sort_index()
    prices = prices[~prices.index.duplicated(keep="first")]
    prices = prices.loc[prices.notna().all(axis=1)]
    if len(prices) < 2 or prices.le(0).any().any():
        raise ValueError("prices must contain at least two complete, positive rows")

    returns = prices.pct_change(fill_method=None).iloc[1:]
    log_returns = np.log(prices).diff().iloc[1:]
    rf_daily = (rf_annual_percent.astype(float) / 100 / 252).rename("rf_daily")
    rf_daily = rf_daily.reindex(rf_daily.index.union(prices.index)).ffill()
    rf_daily = rf_daily.reindex(returns.index)
    if rf_daily.isna().any():
        raise ValueError("risk-free series does not cover the start of the return sample")

    outputs = {
        "prices": prices,
        "returns": returns,
        "log_returns": log_returns,
        "rf_daily": rf_daily.to_frame(),
        "excess_returns": returns.sub(rf_daily, axis=0),
    }
    if macro_available:
        macro = pd.DataFrame(macro_available).sort_index()
        macro = macro.reindex(macro.index.union(prices.index)).ffill()
        outputs["macro"] = macro.reindex(returns.index)
    return outputs

