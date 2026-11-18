"""Prepare common market calendars and explicitly sparse sentiment arrivals.

Run ``python -m src.build_common_sample`` after both data builders. This is
data preparation, not a backtest or a train/validation/test split.
"""

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .audit_data import audit_asset_sentiment, audit_market_bundle
from .paths import PROCESSED_DATA, ROOT
from .provenance import sha256_file


def select_common_dates(returns, rf_daily, *, start, end, window_days, completed_dates):
    """Retain market dates with complete inputs and strictly prior warm-up."""
    if window_days < 1:
        raise ValueError("window_days must be positive")
    if not returns.index.is_unique or not returns.index.is_monotonic_increasing:
        raise ValueError("returns must have sorted unique dates")
    if not returns.index.equals(rf_daily.index):
        raise ValueError("risk-free and return dates must match")
    if not np.isfinite(returns.to_numpy()).all() or not np.isfinite(rf_daily.to_numpy()).all():
        raise ValueError("common market inputs must be complete and finite")
    # Position k has k observations strictly before it; never include today's return.
    ready = np.arange(len(returns)) >= window_days
    mask = ready & (returns.index >= pd.Timestamp(start))
    if end is not None:
        mask &= returns.index <= pd.Timestamp(end)
    mask &= returns.index.isin(completed_dates)
    dates = returns.index[mask]
    if dates.empty:
        raise ValueError("no common dates after coverage and warm-up constraints")
    return dates


def sentiment_arrivals(sentiment, dates, assets):
    """Sum message counts available on each session, not mean daily polarities.

    Weekend and holiday messages can arrive together. Missing arrivals stay
    NaN; no forward fill, hindsight intersection or implied neutral signal.
    """
    if set(sentiment.asset.unique()) != set(assets):
        raise ValueError("sentiment assets differ from expected universe")
    counts = sentiment.groupby(["available_date", "asset"])[["Nbullish", "Nbearish", "N"]].sum()
    labelled = counts.Nbullish + counts.Nbearish
    counts["polarity"] = (counts.Nbullish - counts.Nbearish) / labelled.replace(0, np.nan)
    polarity = counts.polarity.unstack("asset").reindex(index=dates, columns=assets)
    messages = counts.N.unstack("asset").reindex(index=dates, columns=assets)
    return {"sentiment_polarity": polarity, "sentiment_messages": messages,
            "sentiment_observed": messages.notna(),
            "sentiment_labelled": polarity.notna()}


def main():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    tickers = assets + [config["benchmark"]]
    names = ["prices", "returns", "log_returns", "excess_returns", "rf_daily", "macro"]
    frames = {name: pd.read_parquet(PROCESSED_DATA / f"{name}.parquet") for name in names}
    audit_market_bundle(frames, tickers, config["fred_series"]["macro"])
    sentiment = pd.read_parquet(PROCESSED_DATA / "sentiment_asset_daily.parquet")
    audit_asset_sentiment(sentiment, assets + ["MARKET"])
    now = pd.Timestamp.now(tz="UTC")
    schedule = mcal.get_calendar("NYSE").schedule(
        frames["prices"].index.min(), frames["prices"].index.max()
    )
    completed = schedule.index[schedule.market_close <= now]
    window = 252 * config["portfolio"]["estimation_window_years"]
    manifest = {
        "created_utc": datetime.now(UTC).isoformat(), "window_days": window,
        "status": "prepared data, not a frozen test split or validated backtest",
        "sentiment_method": "direct ETF tags, counts aggregated on next NYSE availability session",
        "missing_signal_policy": "retain all common market dates; missing view is not zero; future BL must use no-view anchor or explicitly validated view subset",
        "gics_dependency": "Rebuild after CHECKLIST 1.4b/4.1c; do not substitute company-sector signals silently",
        "final_test_start": config["validation"]["final_test_start"],
        "files": {}, "periods": {},
        "inputs": {name: sha256_file(PROCESSED_DATA / f"{name}.parquet") for name in names},
    }
    manifest["inputs"]["sentiment_asset_daily"] = sha256_file(PROCESSED_DATA / "sentiment_asset_daily.parquet")
    manifest["sentiment_source_coverage"] = {
        asset: {"first_message_date": str(group.date.min().date()),
                "last_message_date": str(group.date.max().date()),
                "first_available_session": str(group.available_date.min().date()),
                "last_available_session": str(group.available_date.max().date())}
        for asset, group in sentiment.groupby("asset")
    }
    coverage = []
    for name, frame in frames.items():
        for column in frame:
            valid = frame[column].dropna()
            coverage.append({"artifact": name, "series": column,
                             "first_date": str(valid.index.min().date()),
                             "last_date": str(valid.index.max().date()), "observations": len(valid)})
    pd.DataFrame(coverage).to_csv(PROCESSED_DATA / "series_coverage.csv", index=False)
    for period, options in config["validation"]["periods"].items():
        dates = select_common_dates(frames["returns"], frames["rf_daily"],
                                    start=options["start"], end=options["end"],
                                    window_days=window, completed_dates=completed)
        outputs = {name: frames[name].loc[dates] for name in names}
        first_pos = frames["returns"].index.get_loc(dates[0])
        outputs["warmup_returns"] = frames["returns"].iloc[first_pos-window:first_pos]
        outputs.update(sentiment_arrivals(sentiment, dates, assets + ["MARKET"]))
        for name, frame in outputs.items():
            path = PROCESSED_DATA / f"common_{period}_{name}.parquet"
            frame.to_parquet(path)
            manifest["files"][path.name] = {"shape": list(frame.shape), "sha256": sha256_file(path)}
        polarity = outputs["sentiment_polarity"]
        manifest["periods"][period] = {
            "requested_start": options["start"], "requested_end": options["end"],
            "first_date": str(dates.min().date()), "last_date": str(dates.max().date()),
            "sessions": len(dates), "strategies": options["strategies"],
            "warmup_first": str(outputs["warmup_returns"].index.min().date()),
            "warmup_last": str(outputs["warmup_returns"].index.max().date()),
            "labelled_sentiment_sessions": {asset: int(polarity[asset].notna().sum()) for asset in polarity},
            "sessions_with_no_labelled_asset": int(polarity.isna().all(axis=1).sum()),
            "last_session_with_any_labelled_sentiment": str(polarity.dropna(how="all").index.max().date()),
        }
        print(period, json.dumps(manifest["periods"][period], indent=2))
    (PROCESSED_DATA / "common_sample_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
