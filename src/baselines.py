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
    return simulate_monthly_targets(returns, targets)[["gross_return", "wealth"]]


def simulate_monthly_targets(
    returns: pd.DataFrame, targets: pd.DataFrame, *, min_turnover: float = 0.,
    cost_bps: float = 0., max_weight: float = 1.,
) -> pd.DataFrame:
    """Simulate fully invested holdings and an optional no-trade threshold.

    Later target trades occur after the decision-session asset moves. Fees
    are a fraction of post-move wealth. The initial invested position is
    shared across variants.
    """
    if not np.isfinite(min_turnover) or not 0 <= min_turnover <= 2:
        raise ValueError("minimum two-way turnover must be in [0, 2]")
    if not np.isfinite(cost_bps) or not 0 <= cost_bps < 5000:
        raise ValueError("cost bps must keep capital positive at maximum turnover")
    if not np.isfinite(max_weight) or not 0 < max_weight <= 1:
        raise ValueError("maximum weight must be in (0, 1]")
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
            or (allocation > max_weight + 1e-9).any()
            or not np.allclose(allocation.sum(axis=1), 1, rtol=0, atol=1e-9)):
        raise ValueError("targets must be finite, long-only, fully invested and within the weight cap")

    events = dict(zip(targets.index[1:], allocation[1:], strict=True))
    weights = allocation[0]
    rate = cost_bps / 10_000
    rows = []
    for date, asset_returns in zip(returns.index, daily, strict=True):
        grown = weights * (1 + asset_returns)
        growth = grown.sum()
        drifted = grown / growth
        weights = drifted
        turnover = 0.
        if date in events:
            target = events[date]
            proposed = np.abs(target - drifted).sum()
            if proposed >= min_turnover or drifted.max() > max_weight + 1e-9:
                weights = target
                turnover = proposed
        cost = turnover * rate
        rows.append((growth - 1, growth * (1 - cost) - 1, turnover, cost))
    result = pd.DataFrame(rows, index=returns.index,
                          columns=["gross_return", "net_return", "turnover", "cost_fraction"])
    result["wealth"] = (1 + result["gross_return"]).cumprod()
    result["net_wealth"] = (1 + result["net_return"]).cumprod()
    return result
