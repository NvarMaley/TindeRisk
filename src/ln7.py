"""LN7 lab checks and a historical event-study reconstruction."""

import numpy as np
import pandas as pd

PRICE_FILE = "sentratio_and_price_closetoclose_adj2.pkl"
EVENT_FILE = "sentratio_and_price_for_pf2.pkl"
EXPECTED_EVENTS = pd.Series({"Good": 454, "Neutral": 294, "Bad": 383}, name="lab_expected")
EXPECTED_SPY = pd.Series(
    [0.016960, 0.002647, 0.000704, 0.004221, 0.003328],
    index=pd.date_range("2010-01-04", periods=5, name="date"),
    name="lab_expected",
)
YEAR_NS = 365 * 24 * 60 * 60 * 10**9


def check_spy_reference(path):
    """Recalculate the five SPY returns shown in Lab LN7, section 1."""
    prices = pd.read_csv(path, usecols=["date", "SPY"], parse_dates=["date"])
    prices = prices.set_index("date", verify_integrity=True).sort_index()
    actual = prices["SPY"].pct_change(fill_method=None).reindex(EXPECTED_SPY.index)
    result = EXPECTED_SPY.to_frame().assign(reproduced=actual.round(6))
    return result.assign(matches=result["reproduced"].eq(result["lab_expected"]))


def _ordered_panel(data):
    panel = data.copy()
    panel["date"] = pd.to_datetime(panel["date"], utc=True)
    if panel[["ticker", "date"]].isna().any().any() or panel.duplicated(["ticker", "date"]).any():
        raise ValueError("LN7 requires unique nonmissing ticker/date keys")
    return panel.sort_values(["ticker", "date"]).reset_index(drop=True)


def _market_residual(data, outcome, benchmark, *, include_today=False):
    """Fit a separate intercept and slope per ticker in a 365-calendar-day window."""
    result = pd.Series(np.nan, index=data.index, dtype=float)
    for _, ticker in data.groupby("ticker", sort=False):
        dates = pd.DatetimeIndex(ticker["date"]).as_unit("ns")
        left = np.searchsorted(dates.asi8, dates.asi8 - YEAR_NS, side="right")
        x = ticker[benchmark].to_numpy(dtype=float, na_value=np.nan)
        y = ticker[outcome].to_numpy(dtype=float, na_value=np.nan)
        valid = np.isfinite(x) & np.isfinite(y)
        residuals = np.full(len(ticker), np.nan)
        for row in np.flatnonzero(valid & (dates > pd.Timestamp("2011-01-01", tz="UTC"))):
            fit = slice(left[row], row + int(include_today))
            x_train, y_train = x[fit][valid[fit]], y[fit][valid[fit]]
            if len(x_train) < 3 or np.ptp(x_train) == 0:
                continue
            slope, intercept = np.linalg.lstsq(
                np.column_stack([x_train, np.ones(len(x_train))]), y_train, rcond=None
            )[0]
            residuals[row] = y[row] - (intercept + slope * x[row])
        result.loc[ticker.index] = residuals
    return result


def abnormal_returns(prices):
    """Use the lab's SPY-only regression, with the endpoint included as shown."""
    panel = _ordered_panel(prices[["ticker", "date", "daily_return"]])
    spy = panel.loc[panel["ticker"].eq("SPY")].set_index("date")["daily_return"]
    if spy.empty:
        raise ValueError("The LN7 price panel must contain SPY")
    panel["market_return"] = panel["date"].map(spy)
    panel["AR"] = _market_residual(panel, "daily_return", "market_return", include_today=True)
    return panel


def reconstruct_events(messages):
    """Reconstruct volume and polarity market models on instructor-aligned data."""
    panel = _ordered_panel(messages)
    labelled = panel["Nbullish"] + panel["Nbearish"]
    panel["count_polarity"] = (panel["Nbullish"] - panel["Nbearish"]) / labelled.where(labelled > 0)
    # Preserve Moodle's supplied, aligned Polarity and its market benchmark.
    panel["AP"] = _market_residual(panel, "Polarity", "market_polarity")
    groups = panel.groupby("ticker", sort=False)
    for source, target in (("N", "volume_change"), ("total_vol_tweet", "market_volume_change")):
        previous = groups[source].shift()
        panel[target] = panel[source] / previous.where(previous > 0) - 1
    panel["AV"] = _market_residual(panel, "volume_change", "market_volume_change")

    z_score = pd.Series(np.nan, index=panel.index, dtype=float)
    for _, ticker in panel.groupby("ticker", sort=False):
        av = ticker.set_index("date")["AV"]
        history = av.rolling("365D", min_periods=2, closed="left")
        sd = history.std()
        z_score.loc[ticker.index] = ((av - history.mean()) / sd.where(sd > 0)).to_numpy()
    panel["AV_z"] = z_score
    panel["event"] = panel["AV_z"].gt(2) & panel["businessday"].eq(True)
    ap = panel["AP"]
    panel["event_type"] = pd.Series(pd.NA, index=panel.index, dtype="string")
    panel.loc[panel["event"] & ap.notna(), "event_type"] = "Neutral"
    panel.loc[panel["event"] & ap.gt(0.07), "event_type"] = "Good"
    panel.loc[panel["event"] & ap.lt(-0.03), "event_type"] = "Bad"
    return panel


def event_paths(panel, radius=20):
    """Calculate CAR/CAP in trading-session event time for complete windows."""
    windows = []
    session_dates = pd.DatetimeIndex(
        panel.loc[panel["market_return"].notna() & panel["businessday"].eq(True), "date"].unique()
    ).sort_values()
    for ticker, group in panel.groupby("ticker", sort=False):
        sessions = group.set_index("date", drop=False).reindex(session_dates)
        for center in np.flatnonzero(sessions["event_type"].notna()):
            if center < radius or center + radius >= len(sessions):
                continue
            window = sessions.iloc[center - radius : center + radius + 1]
            if window[["AR", "AP"]].isna().any().any():
                continue
            path = window[["AR", "AP"]].cumsum().rename(columns={"AR": "CAR", "AP": "CAP"})
            paths = path.assign(
                ticker=ticker, event_date=sessions["date"].iloc[center],
                event_type=sessions["event_type"].iloc[center],
                relative_session=np.arange(-radius, radius + 1),
            )
            windows.append(paths)
    columns = ["CAR", "CAP", "ticker", "event_date", "event_type", "relative_session"]
    return pd.concat(windows, ignore_index=True) if windows else pd.DataFrame(columns=columns)


def run_moodle(directory):
    """Read the original local files only if obtained from the course."""
    prices = abnormal_returns(pd.read_pickle(directory / PRICE_FILE))
    messages = reconstruct_events(pd.read_pickle(directory / EVENT_FILE))
    panel = messages.merge(
        prices[["ticker", "date", "market_return", "AR"]],
        on=["ticker", "date"], how="left", validate="one_to_one", suffixes=("_supplied", ""),
    )
    supplied = panel.loc[panel["Event3"].eq(True), "Type"].value_counts()
    rebuilt = panel["event_type"].value_counts()
    counts = EXPECTED_EVENTS.to_frame()
    counts["moodle_labels"] = supplied.reindex(counts.index, fill_value=0)
    counts["reconstructed"] = rebuilt.reindex(counts.index, fill_value=0)
    return panel, counts, event_paths(panel)
