"""Calibrate the Black–Litterman Q vector on completed historical spreads."""

from collections.abc import Mapping

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

SESSIONS_PER_YEAR = 252


def monthly_view_outcomes(
    views_by_month: Mapping[pd.Period, pd.DataFrame],
    daily_returns: pd.DataFrame,
    *,
    before_month,
) -> pd.DataFrame:
    """Project realized daily returns onto each month's pre-existing view.

    The holding period runs from the first NYSE close to the last, skipping
    months at or after the exclusive cutoff and omitting incomplete outcomes.
    Results are average daily spreads, in decimal units.
    """
    cutoff = pd.Period(before_month, freq="M")
    if pd.isna(cutoff):
        raise ValueError("An exclusive holding-month cutoff is required")
    if not isinstance(daily_returns.index, pd.DatetimeIndex) or not daily_returns.index.is_unique:
        raise ValueError("Returns require unique session dates")
    calendar = mcal.get_calendar("NYSE")
    outcomes = {}
    for month, views in sorted(views_by_month.items()):
        if month >= cutoff or views.empty:
            continue
        if views.columns.has_duplicates or views.index.has_duplicates:
            raise ValueError("Historical views require unique asset and view labels")
        sessions = calendar.valid_days(month.start_time, month.end_time.normalize(), tz=None)
        if not sessions.isin(daily_returns.index).all():
            continue
        for view, exposure in views.iterrows():
            legs = exposure[exposure.ne(0)]
            if len(legs) < 2 or not np.isfinite(legs).all() or not np.isclose(legs.sum(), 0):
                raise ValueError("Each historical view must be a finite relative spread")
            realized = daily_returns.loc[sessions[1:], legs.index].to_numpy(dtype=float)
            if np.isfinite(realized).all():
                outcomes.setdefault(month, {})[view] = float((realized @ legs.to_numpy()).mean())
    return pd.DataFrame.from_dict(outcomes, orient="index").set_axis(
        pd.PeriodIndex(outcomes.keys(), freq="M", name="holding_month")
    )


def estimate_relative_q(
    proposed_p: pd.DataFrame, history: pd.DataFrame, *, validation_start,
    final_test_start, decision_date,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Return the active P rows, aligned annualized Q and eligibility diagnostics."""
    q = pd.Series(dtype=float, name="Q", index=proposed_p.index[:0])
    diagnostics = pd.DataFrame(index=proposed_p.index, columns=[
        "status", "train_months", "validation_months", "train_spread_daily",
        "validation_spread_daily", "validation_mae", "zero_mae", "validation_mse",
    ])
    if proposed_p.empty:
        return proposed_p, q, diagnostics
    if final_test_start is None:
        diagnostics["status"] = "final_test_boundary_missing"
        return proposed_p.iloc[:0], q, diagnostics

    validation_month = pd.Period(validation_start, freq="M")
    test_month = pd.Period(final_test_start, freq="M")
    decision_month = pd.Period(decision_date, freq="M")
    if any(pd.isna(value) for value in (validation_month, test_month, decision_month)):
        raise ValueError("Calibration requires valid validation, test and decision dates")
    if validation_month >= test_month:
        raise ValueError("Validation must start before the final test")
    if (not isinstance(history.index, pd.PeriodIndex) or history.index.freqstr != "M"
            or history.index.hasnans or not history.index.is_unique or history.columns.has_duplicates
            or proposed_p.index.has_duplicates):
        raise ValueError("Q history requires unique holding months and view labels")

    cutoff = min(decision_month, test_month)
    past = history.loc[history.index < cutoff].reindex(columns=proposed_p.index)
    for view in proposed_p.index:
        spread = past[view].astype(float)
        spread = spread[np.isfinite(spread)]
        train = spread.loc[spread.index < validation_month]
        validation = spread.loc[spread.index >= validation_month]
        train_mean, validation_mean = train.mean(), validation.mean()
        errors = validation - train_mean
        mae = errors.abs().mean()
        zero_mae = validation.abs().mean()
        if len(train) < 24 or len(validation) < 12:
            status = "insufficient_history"
        elif train_mean <= 0 or validation_mean <= 0 or mae >= zero_mae:
            status = "unstable"
        else:
            status = "active"
            q.loc[view] = float(spread.mean() * SESSIONS_PER_YEAR)
        diagnostics.loc[view] = [status, len(train), len(validation), train_mean,
                                 validation_mean, mae, zero_mae, errors.pow(2).mean()]

    return proposed_p.loc[q.index], q, diagnostics
