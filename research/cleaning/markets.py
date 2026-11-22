"""Dated US sessions, ETF total returns, cash proxies and retrospective price diagnostics."""

import json

import exchange_calendars as xc
import numpy as np
import pandas as pd

from .availability import exact_vintage_price

SLEEVE = ["SPY", "IEF", "GLD"]


def schedule(venue):
    return xc.get_calendar(venue, start="1997-01-01", end="2027-12-31").schedule[
        ["open", "close"]
    ]


def dated_csv(path):
    frame = pd.read_csv(path, index_col=0, parse_dates=[0], na_values=["."])
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError(f"Duplicate or unordered observation dates in {path}")
    return frame


def cash_accrual(discount_percent, days):
    # Fixed 91-day discount bill bought at par minus discount. Hold-to-maturity equivalent accrual.
    price = 1 - discount_percent / 100 * 91 / 360
    if (price <= 0).any():
        raise ValueError("Bill price must be positive")
    return (1 / price) ** (days / 91) - 1


def market_panel(data, output):
    raw = data / "raw"
    levels = dated_csv(raw / "etf_prices_adjusted.csv")
    observed_fx = dated_csv(raw / "public_phase2/DEXSZUS.csv").iloc[:, 0]
    download = json.loads((data / "processed/metadata.json").read_text())["downloads"][
        "prices"
    ]["downloaded_at_utc"]
    series, quality, sensitivities = [], [], []
    for path in sorted((raw / "price_events").glob("*.json")):
        envelope = json.loads(path.read_text())
        chart = json.loads(envelope["payload"])["chart"]["result"][0]
        meta = chart["meta"]
        ticker = meta["symbol"]
        venue = {"PCX": "ARCX", "NGM": "XNAS"}[meta["exchangeName"]]
        cal = schedule(venue).loc[levels.index.min() : levels.index.max()]
        timestamps = pd.to_datetime(chart["timestamp"], unit="s", utc=True)
        days = (
            timestamps.tz_convert(meta["exchangeTimezoneName"])
            .normalize()
            .tz_localize(None)
        )
        if (
            days.has_duplicates
            or not days.isin(cal.index).all()
            or not levels.index.isin(cal.index).all()
        ):
            raise ValueError(f"Duplicate or off-calendar date for {ticker}")
        frame = pd.DataFrame(index=cal.index)
        frame.index.name = "session"
        frame["asset"], frame["venue"], frame["snapshot_utc"] = (
            ticker,
            venue,
            pd.Timestamp(download),
        )
        frame["decision_at"] = cal.close
        frame["next_scheduled_open"] = schedule(venue).open.shift(-1).reindex(cal.index)
        frame["adjusted_usd_raw"] = levels[ticker]
        frame["provisional_close"] = frame.decision_at > frame.snapshot_utc
        frame["adjusted_usd"] = frame.adjusted_usd_raw.where(
            frame.adjusted_usd_raw.gt(0) & ~frame.provisional_close
        )
        # The chart close is already split-normalized. Applying the split ratio again double counts it.
        frame["chart_open_proxy_usd"] = pd.Series(
            chart["indicators"]["quote"][0]["open"], index=days
        )
        frame["chart_close"] = pd.Series(
            chart["indicators"]["quote"][0]["close"], index=days
        )
        frame["chart_snapshot_utc"] = pd.Timestamp(envelope["retrieved"])
        frame["distribution_usd"] = 0.0
        frame["split_ratio"] = 1.0
        for kind in ("dividends", "capitalGains", "splits"):
            for event in chart.get("events", {}).get(kind, {}).values():
                day = (
                    pd.Timestamp(event["date"], unit="s", tz="UTC")
                    .tz_convert(meta["exchangeTimezoneName"])
                    .tz_localize(None)
                    .normalize()
                )
                if day not in cal.index:
                    raise ValueError(f"Off-calendar event {ticker} {day}")
                if kind == "splits":
                    frame.loc[day, "split_ratio"] *= (
                        event["numerator"] / event["denominator"]
                    )
                else:
                    frame.loc[day, "distribution_usd"] += event["amount"]
        frame["usd_return"] = frame.adjusted_usd.pct_change(fill_method=None)
        frame["event_return"] = (
            frame.chart_close + frame.distribution_usd
        ) / frame.chart_close.shift() - 1
        frame["reconciliation_error"] = frame.usd_return - frame.event_return
        frame["chf_per_usd"] = observed_fx.reindex(cal.index)
        if (frame.chf_per_usd.dropna() <= 0).any():
            raise ValueError("Invalid CHF per USD observation")
        fx = frame.chf_per_usd.pct_change(fill_method=None)
        frame["fx_return"] = fx
        frame["chf_return"] = (1 + frame.usd_return) * (1 + fx) - 1
        frame["flat_run"] = (
            frame.usd_return.eq(0).groupby(frame.usd_return.ne(0).cumsum()).cumsum()
        )
        # Ex-post flags belong to the audit, never to a predictor or investability filter.
        years = frame.index.year
        median = frame.usd_return.groupby(years).transform("median")
        dev = (frame.usd_return - median).abs()
        mad = dev.groupby(years).transform("median")
        frame["mad_flag"] = mad.gt(0) & dev.gt(8 * 1.4826 * mad)
        frame["source_gap_flag"] = frame.reconciliation_error.abs().gt(0.001)
        frame["review"] = np.select(
            [
                frame.provisional_close,
                frame.adjusted_usd.isna(),
                frame.source_gap_flag,
                frame.mad_flag & frame.distribution_usd.ne(0),
                frame.mad_flag & frame.split_ratio.ne(1),
                frame.mad_flag,
            ],
            [
                "before official close; excluded",
                "missing/invalid; excluded",
                "source difference >10bp; unresolved",
                "extreme; distribution recorded",
                "extreme; split recorded",
                "extreme; compare chart return",
            ],
            default="",
        )
        for year, group in frame.groupby(years):
            quality.append(
                {
                    "asset": ticker,
                    "year": year,
                    "sessions": len(group),
                    "duplicates": 0,
                    "missing_adjusted": group.adjusted_usd_raw.isna().sum(),
                    "provisional": group.provisional_close.sum(),
                    "missing_fx": group.chf_per_usd.isna().sum(),
                    "flat_sessions": group.usd_return.eq(0).sum(),
                    "longest_flat_run": group.flat_run.max(),
                    "mad_flags": group.mad_flag.sum(),
                    "source_gaps": group.source_gap_flag.sum(),
                    "usd_returns": group.usd_return.count(),
                    "chf_returns": group.chf_return.count(),
                }
            )
        comparisons = pd.concat(
            [
                frame.usd_return.rename("usd"),
                fx.rename("same"),
                fx.shift(1).rename("lag"),
                fx.shift(-1).rename("lead"),
            ],
            axis=1,
        ).dropna()
        for name in ("same", "lag", "lead"):
            chf = (1 + comparisons.usd) * (1 + comparisons[name]) - 1
            sensitivities.append(
                {
                    "asset": ticker,
                    "fx_alignment": name,
                    "common_pairs": len(chf),
                    "daily_sd": chf.std(),
                    "correlation_usd_fx": comparisons.usd.corr(comparisons[name]),
                }
            )
        for name, rates in [
            ("observed FX only", frame.chf_per_usd),
            ("carried FX sensitivity only", frame.chf_per_usd.ffill()),
        ]:
            test_fx = rates.pct_change(fill_method=None)
            test_return = (1 + frame.usd_return) * (1 + test_fx) - 1
            sensitivities.append(
                {
                    "asset": ticker,
                    "fx_alignment": name,
                    "common_pairs": test_return.count(),
                    "daily_sd": test_return.std(),
                    "correlation_usd_fx": frame.usd_return.corr(test_fx),
                }
            )
        frame = frame.reset_index()
        decisions = frame[["asset", "session", "decision_at"]]
        quotes = frame[["asset", "session", "snapshot_utc", "adjusted_usd"]].rename(
            columns={"snapshot_utc": "known_at", "adjusted_usd": "as_received_level"}
        )
        frame["level_known_at_decision"] = exact_vintage_price(
            decisions, quotes
        ).as_received_level.array
        series.append(frame)
    panel = pd.concat(series, ignore_index=True)
    if (
        set(panel.asset) != set(levels)
        or panel.duplicated(["asset", "session", "snapshot_utc"]).any()
    ):
        raise ValueError("Market coverage/key mismatch")
    panel.to_parquet(output / "market.parquet", index=False)
    pd.DataFrame(quality).to_csv(output / "quality_by_year.csv", index=False)
    pd.DataFrame(sensitivities).to_csv(output / "fx_alignment.csv", index=False)
    panel.loc[
        panel.review.ne(""),
        [
            "asset",
            "session",
            "adjusted_usd_raw",
            "adjusted_usd",
            "usd_return",
            "event_return",
            "distribution_usd",
            "split_ratio",
            "reconciliation_error",
            "review",
        ],
    ].to_csv(output / "market_exceptions.csv", index=False)
    return panel
