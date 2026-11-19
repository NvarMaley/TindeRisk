"""Portfolio risk, risk budgeting, Black–Litterman means and cash scaling."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _covariance(covariance: pd.DataFrame, *, positive_definite: bool = False) -> np.ndarray:
    assets = covariance.columns
    if assets.empty or assets.has_duplicates or assets.hasnans or not covariance.index.equals(assets):
        raise ValueError("covariance labels must match and be unique")
    matrix = covariance.to_numpy(dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError("covariance must be finite")
    scale = np.max(np.abs(matrix))
    tolerance = 1e-12 * scale
    if not np.allclose(matrix, matrix.T, rtol=0, atol=tolerance):
        raise ValueError("covariance must be symmetric")
    matrix = (matrix + matrix.T) / 2
    smallest = np.linalg.eigvalsh(matrix)[0]
    if positive_definite and smallest <= 0:
        raise ValueError("covariance must be positive definite")
    if smallest < -tolerance:
        raise ValueError("covariance must be positive semidefinite")
    return matrix


def _aligned_values(vector: pd.Series, labels: pd.Index, name: str) -> np.ndarray:
    if not vector.index.equals(labels):
        raise ValueError(f"{name} labels must match the supplied order")
    values = vector.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{name} must be finite")
    return values


def _volatility(weights: np.ndarray, matrix: np.ndarray) -> float:
    return float(np.sqrt(max(float(weights @ matrix @ weights), 0.0)))


def vol(weights: pd.Series, covariance: pd.DataFrame) -> float:
    """Return standard deviation in the units of the covariance horizon."""
    return _volatility(_aligned_values(weights, covariance.columns, "weights"), _covariance(covariance))


def risk_contrib(weights: pd.Series, covariance: pd.DataFrame) -> pd.Series:
    """Return signed Euler contributions to standard deviation."""
    matrix = _covariance(covariance)
    values = _aligned_values(weights, covariance.columns, "weights")
    volatility = _volatility(values, matrix)
    if volatility == 0:
        raise ValueError("risk contributions require positive portfolio volatility")
    return pd.Series(values * (matrix @ values) / volatility, index=covariance.columns)


def tracking_error(weights: pd.Series, reference: pd.Series, covariance: pd.DataFrame) -> float:
    """Return the standard deviation of active weights against the reference."""
    values = _aligned_values(weights, covariance.columns, "weights")
    benchmark = _aligned_values(reference, covariance.columns, "reference weights")
    return _volatility(values - benchmark, _covariance(covariance))


def risk_budget(covariance: pd.DataFrame, budgets: pd.Series) -> pd.Series:
    """Solve the convex log-barrier problem for positive, unit-sum risk budgets."""
    sigma = _covariance(covariance, positive_definite=True)
    target = _aligned_values(budgets, covariance.columns, "risk budgets")
    if (target <= 0).any() or not np.isclose(target.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("risk budgets must be strictly positive and sum to one")
    stdev = np.sqrt(sigma.diagonal())
    correlation = sigma / np.outer(stdev, stdev)
    positions = np.sqrt(target)

    # Each coordinate minimizes the objective holding the others fixed.
    for _ in range(10_000):
        for i, budget in enumerate(target):
            cross = correlation[i] @ positions - positions[i]
            root = np.hypot(cross, 2 * np.sqrt(budget))
            positions[i] = 2 * budget / (root + cross) if cross >= 0 else (root - cross) / 2
        if np.max(np.abs(positions * (correlation @ positions) - target)) <= 1e-10:
            weights = positions / stdev
            return pd.Series(weights / weights.sum(), index=covariance.columns)
    raise RuntimeError("risk-budget optimization did not converge")


def erc(covariance: pd.DataFrame) -> pd.Series:
    """Compute a fully invested, long-only portfolio with equal risk shares."""
    assets = covariance.columns
    if assets.empty:
        raise ValueError("ERC requires at least one asset")
    return risk_budget(covariance, pd.Series(1 / len(assets), index=assets))


def bl_posterior(prior: pd.Series, covariance: pd.DataFrame, p: pd.DataFrame,
                 q: pd.Series, omega: pd.DataFrame, *, tau: float) -> pd.Series:
    """Update the prior mean, using a common horizon for prior, covariance and views."""
    sigma = _covariance(covariance)
    assets = covariance.columns
    mu = _aligned_values(prior, assets, "prior")
    views = p.index
    if (not p.columns.equals(assets) or views.has_duplicates or views.hasnans
            or not omega.index.equals(views) or not omega.columns.equals(views)):
        raise ValueError("P and Omega must use matching asset and unique view labels")
    forecast = _aligned_values(q, views, "Q")
    if not np.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be positive and finite")
    if views.empty:
        return prior.copy()
    exposures = p.to_numpy(dtype=float)
    if not np.isfinite(exposures).all() or (exposures == 0).all(axis=1).any():
        raise ValueError("view exposures must be finite and nonzero")
    cov_with_views = tau * sigma @ exposures.T
    system = exposures @ cov_with_views + _covariance(omega)
    try:
        np.linalg.cholesky((system + system.T) / 2)
        adjustment = np.linalg.solve(system, forecast - exposures @ mu)
    except np.linalg.LinAlgError as exc:
        raise ValueError("view covariance must be invertible") from exc
    return pd.Series(mu + cov_with_views @ adjustment, index=assets, name=prior.name)


@dataclass(frozen=True)
class TargetAllocation:
    risky_weights: pd.Series
    cash_weight: float
    achieved_volatility: float


def target_vol(weights: pd.Series, covariance: pd.DataFrame, target: float, *,
               max_risky_exposure: float = 1.0, max_etf_weight: float | None = 1.0) -> TargetAllocation:
    """Scale a fully invested long-only sleeve and put the remainder in cash."""
    values = _aligned_values(weights, covariance.columns, "risky weights")
    matrix = _covariance(covariance)
    if (values < 0).any() or not np.isclose(values.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("risky sleeve must be fully invested and long-only")
    if not np.isfinite(target) or target < 0:
        raise ValueError("target volatility must be nonnegative and finite")
    if not np.isfinite(max_risky_exposure) or max_risky_exposure <= 0:
        raise ValueError("invalid allocation limits")
    if max_etf_weight is not None and (not np.isfinite(max_etf_weight) or not 0 < max_etf_weight <= 1):
        raise ValueError("invalid allocation limits")
    volatility = _volatility(values, matrix)
    if volatility == 0:
        raise ValueError("risky sleeve volatility must be positive")
    exposure = min(target / volatility, max_risky_exposure)
    if max_etf_weight is not None:
        exposure = min(exposure, max_etf_weight / values.max())
    actual = weights * exposure
    return TargetAllocation(actual, float(1 - actual.sum()), _volatility(values * exposure, matrix))
