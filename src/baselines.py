"""Long-only baseline allocation and daily drift between rebalances."""

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from scipy.optimize import minimize


def minimum_variance_weights(covariance: pd.DataFrame, max_weight: float) -> pd.Series:
    """Minimize variance while fully invested, long-only and capped per asset."""
    labels = covariance.columns
    matrix = covariance.to_numpy(dtype=float)
    n = len(labels)
    if not n or not labels.is_unique or not covariance.index.equals(labels):
        raise ValueError("covariance labels must match and be unique")
    if not np.isfinite(max_weight) or not 1 / n <= max_weight <= 1:
        raise ValueError("infeasible maximum asset weight")
    if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, atol=1e-14):
        raise ValueError("covariance must be finite and symmetric")
    if np.linalg.eigvalsh(matrix).min() <= 0:
        raise ValueError("covariance must be positive definite")

    # Scale the objective to keep the solver's tolerance independent of units.
    matrix = matrix / np.max(np.diag(matrix))
    initial = np.full(n, 1 / n)
    if max_weight == 1 / n:
        return pd.Series(initial, index=labels)
    solution = minimize(
        lambda weights: .5 * weights @ matrix @ weights, initial,
        jac=lambda weights: matrix @ weights,
        bounds=[(0, max_weight)] * n,
        constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1,
                     "jac": lambda weights: np.ones(n)},
        method="SLSQP", options={"ftol": 1e-12},
    )
    weights = solution.x
    if (not solution.success or not np.isfinite(weights).all()
            or abs(weights.sum() - 1) > 1e-9 or weights.min() < -1e-9
            or weights.max() > max_weight + 1e-9):
        raise RuntimeError(f"minimum-variance optimization failed: {solution.message}")
    return pd.Series(weights, index=labels)


def benchmark_60_40_weights(equity: str = "SPY") -> pd.Series:
    """Return the fully invested equity/bond benchmark targets."""
    if not equity or equity == "IEF":
        raise ValueError("60/40 requires an equity ticker distinct from IEF")
    return pd.Series([.6, .4], index=[equity, "IEF"])


def monthly_decision_closes(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the initial NYSE month-end and the closes that can affect the sample."""
    if (not isinstance(sessions, pd.DatetimeIndex) or sessions.empty or sessions.tz is not None
            or sessions.hasnans or not sessions.is_unique or not sessions.is_monotonic_increasing):
        raise ValueError("monthly decisions require sorted unique NYSE session dates")
    first, last = sessions[[0, -1]]
    previous_month = first.to_period("M") - 1
    calendar = mcal.get_calendar("NYSE")
    schedule = calendar.valid_days(previous_month.start_time, last + pd.offsets.MonthEnd(0), tz=None)
    if not sessions.equals(schedule[(schedule >= first) & (schedule <= last)]):
        raise ValueError("returns must cover all scheduled NYSE sessions")
    month_ends = schedule[~schedule.to_period("M").duplicated(keep="last")]
    return month_ends[month_ends < last]


def apply_monthly_targets(returns: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    """Carry holdings forward until an after-close target applies next session.

    Output columns record the portfolio return and gross wealth. The first
    target must precede the sample. Other target dates must be return dates.
    """
    if returns.empty or targets.empty or not returns.columns.equals(targets.columns):
        raise ValueError("returns and targets must be nonempty with matching assets")
    if any(not idx.is_unique or not idx.is_monotonic_increasing or idx.hasnans
           for idx in (returns.index, targets.index)):
        raise ValueError("dates must be sorted, unique and nonmissing")
    if targets.index[0] >= returns.index[0] or not targets.index[1:].isin(returns.index[:-1]).all():
        raise ValueError("targets must precede the sessions they can affect")
    daily = returns.to_numpy(dtype=float)
    allocation = targets.to_numpy(dtype=float)
    if not np.isfinite(daily).all() or (daily <= -1).any():
        raise ValueError("asset returns must be finite and strictly above -1")
    if (not np.isfinite(allocation).all() or (allocation < -1e-9).any()
            or not np.allclose(allocation.sum(axis=1), 1, rtol=0, atol=1e-9)):
        raise ValueError("targets must be finite, long-only and fully invested")

    events = dict(zip(targets.index[1:], allocation[1:], strict=True))
    weights = allocation[0]
    portfolio_returns = []
    for date, asset_returns in zip(returns.index, daily, strict=True):
        grown = weights * (1 + asset_returns)
        growth = grown.sum()
        portfolio_returns.append(growth - 1)
        weights = events[date] if date in events else grown / growth
    result = pd.DataFrame({"gross_return": portfolio_returns}, index=returns.index)
    result["wealth"] = (1 + result["gross_return"]).cumprod()
    return result
