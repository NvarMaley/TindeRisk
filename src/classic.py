"""Classic long-only risky sleeve fit at a specified market close."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .baselines import minimum_variance_weights
from .estimation import ledoit_wolf_constant_corr, trailing_returns_at_close
from .expected_returns import rolling_expected_returns
from .optim import _aligned_values, _covariance


@dataclass(frozen=True)
class ClassicPortfolio:
    weights: pd.Series
    annual_excess_mean: pd.Series
    annual_covariance: pd.DataFrame
    method: str


def classic_weights(annual_excess_mean: pd.Series, annual_covariance: pd.DataFrame,
                    max_weight: float) -> tuple[pd.Series, str]:
    """Maximize positive ex-ante Sharpe, using capped GMV if no positive fit exists."""
    covariance = _covariance(annual_covariance, positive_definite=True)
    assets = annual_covariance.columns
    mean = _aligned_values(annual_excess_mean, assets, "expected excess returns")
    n = len(assets)
    if not np.isfinite(max_weight) or not 1 / n <= max_weight <= 1:
        raise ValueError("infeasible maximum asset weight")

    # Filling the highest-mean assets first finds the attainable maximum mean.
    order = np.argsort(-mean, kind="stable")
    initial = np.zeros(n)
    initial[order] = np.clip(1 - max_weight * np.arange(n), 0, max_weight)
    best_mean = mean @ initial
    if best_mean <= 0:
        return minimum_variance_weights(annual_covariance, max_weight), "gmv_nonpositive"
    if max_weight == 1 / n:
        return pd.Series(1 / n, index=assets), "tangency"

    # Normalize the expected return of the maximum-mean feasible portfolio to one.
    # In these coordinates, minimizing variance solves the maximum-Sharpe problem.
    scaled_mean = mean / best_mean
    matrix = covariance / np.max(covariance.diagonal())
    cap_constraints = max_weight - np.eye(n)
    solution = minimize(
        lambda weights: .5 * weights @ matrix @ weights, initial,
        jac=lambda weights: matrix @ weights,
        bounds=[(0, None)] * n,
        constraints=[
            {"type": "eq", "fun": lambda weights: scaled_mean @ weights - 1,
             "jac": lambda weights: scaled_mean},
            {"type": "ineq", "fun": lambda weights: cap_constraints @ weights,
             "jac": lambda weights: cap_constraints},
        ],
        method="SLSQP", options={"ftol": 1e-12, "maxiter": 300},
    )
    scaled_weights = solution.x
    if (not solution.success or not np.isfinite(scaled_weights).all()
            or not np.isclose(scaled_mean @ scaled_weights, 1, atol=1e-9, rtol=0)
            or scaled_weights.sum() <= 0):
        raise RuntimeError(f"Classic tangency optimization failed: {solution.message}")
    weights = scaled_weights / scaled_weights.sum()
    if (weights.min() < 0 or weights.max() > max_weight + 1e-9
            or weights @ mean <= 0):
        raise RuntimeError("Classic tangency returned infeasible weights")
    return pd.Series(weights, index=assets), "tangency"


def fit_classic(returns: pd.DataFrame, excess_returns: pd.DataFrame, *,
                decision_date: pd.Timestamp, max_weight: float, window: int = 756) -> ClassicPortfolio:
    """Fit Classic on a trailing window through the decision close inclusive."""
    date = pd.Timestamp(decision_date)
    history = trailing_returns_at_close(returns, date, window)
    excess = excess_returns.loc[excess_returns.index.isin(history.index)]
    means, _, _ = rolling_expected_returns(history, excess, pd.DatetimeIndex([date]), window=window)
    covariance, _ = ledoit_wolf_constant_corr(history)
    mean = means.iloc[0]
    weights, method = classic_weights(mean, covariance, max_weight)
    return ClassicPortfolio(weights, mean, covariance, method)
