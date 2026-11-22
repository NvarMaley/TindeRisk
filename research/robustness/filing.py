"""One manually matched EDGAR filing, used to demonstrate dated characteristics."""

import numpy as np
import pandas as pd


def characteristics(filing, security, calendar, origin):
    origin = pd.Timestamp(origin)
    accepted = pd.Timestamp(filing["accepted_at"]).tz_convert("America/New_York")
    cutoff = max(
        accepted.tz_localize(None).normalize(), pd.Timestamp(filing["filed_date"])
    )
    after = pd.DatetimeIndex(calendar).sort_values()
    eligible = after[after > cutoff]
    if not len(eligible) or origin < eligible[0]:
        raise ValueError("Filing unavailable at decision")
    sec = filing["security"]
    rows = security.loc[security.permno == sec["permno"]].copy()
    rows["day"] = pd.to_datetime(rows.day)
    now = rows[rows.day == origin]
    if len(now) != 1:
        raise ValueError("Expected one decision-date security")
    r = now.iloc[0]
    if not (
        r.best_link_count == 1
        and r.gvkey == sec["gvkey"]
        and r.common_us
        and r.market_candidate
        and r.cap_thousands > 0
    ):
        raise ValueError("Ineligible security or accounting link")
    hist = rows.set_index(rows.day.dt.to_period("M")).ret
    month = origin.to_period("M")
    window = hist.reindex(pd.period_range(month - 11, month - 1, freq="M"))
    if not np.isfinite(window).all():
        raise ValueError("Incomplete trailing momentum")
    return {
        "accession": filing["accession"],
        "permno": sec["permno"],
        "gvkey": r.gvkey,
        "first_allowed_session": str(eligible[0].date()),
        "origin": str(origin.date()),
        "holding_month": str(month + 1),
        "book_to_market": (filing["total_equity"] - filing["preferred_equity"])
        / (r.cap_thousands / 1000),
        "gross_profitability": (filing["sales"] - filing["cost_of_sales"])
        / filing["assets"],
        "asset_growth": filing["assets"] / filing["prior_assets"] - 1,
        "momentum": float((1 + window).prod() - 1),
        "momentum_start": str(window.index[0]),
        "momentum_end": str(window.index[-1]),
    }
