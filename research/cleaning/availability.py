"""Availability and fallback primitives used by the prepared release."""

import pandas as pd


def exact_vintage_price(decisions, quotes):
    """Match the requested session and asset to a quote version actually known before the cutoff."""
    by = ["asset", "session"]
    decisions = decisions.assign(
        decision_at=decisions.decision_at.astype("datetime64[ns, UTC]")
    )
    quotes = quotes.assign(known_at=quotes.known_at.astype("datetime64[ns, UTC]"))
    if quotes.duplicated([*by, "known_at"]).any():
        raise ValueError("Ambiguous quote vintage")
    return pd.merge_asof(
        decisions.sort_values("decision_at"),
        quotes.sort_values("known_at"),
        by=by,
        left_on="decision_at",
        right_on="known_at",
        direction="backward",
        allow_exact_matches=False,
    )


def eligible_session(prices, fx):
    """Return the first fully quoted session in the supplied post-decision window."""
    usable = prices.gt(0).all(axis=1) & fx.reindex(prices.index).gt(0)
    return usable.index[usable][0] if usable.any() else pd.NaT
