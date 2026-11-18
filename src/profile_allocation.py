"""Scale a supplied risky portfolio to the effective profile target."""

from dataclasses import dataclass
from math import isfinite

import numpy as np
import pandas as pd

from .profiling import RiskTarget, risk_target


@dataclass(frozen=True)
class ProfileAllocation:
    target: RiskTarget
    risky_weights: pd.Series
    cash_weight: float
    achieved_volatility: float


def allocate_for_profile(risky_weights: pd.Series, annual_covariance: pd.DataFrame, *,
                         risk_aversion: float, reference_sharpe: float, capacity: float,
                         max_risky_exposure: float = 1., max_etf_weight: float = 1.) -> ProfileAllocation:
    """Mix the risky sleeve and cash, then measure risk on the actual weights."""
    if (not risky_weights.index.is_unique or not risky_weights.index.equals(annual_covariance.index)
            or not risky_weights.index.equals(annual_covariance.columns)):
        raise ValueError("risky weights and covariance must use matching ETF labels")
    weights = risky_weights.to_numpy(dtype=float)
    covariance = annual_covariance.to_numpy(dtype=float)
    if not np.isfinite(weights).all() or (weights < 0).any() or not np.isclose(weights.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("risky sleeve must be fully invested and long-only")
    if (not np.isfinite(covariance).all() or not np.allclose(covariance, covariance.T, atol=1e-12)
            or np.linalg.eigvalsh(covariance)[0] < -1e-12):
        raise ValueError("annual covariance must be finite, symmetric, and positive semidefinite")
    if (not isfinite(max_risky_exposure) or max_risky_exposure <= 0
            or not isfinite(max_etf_weight) or not 0 < max_etf_weight <= 1):
        raise ValueError("invalid allocation limits")
    variance = float(weights @ covariance @ weights)
    if variance <= 0:
        raise ValueError("risky sleeve volatility must be positive")
    target = risk_target(risk_aversion, reference_sharpe, capacity)
    exposure = min(target.effective / np.sqrt(variance), max_risky_exposure,
                   max_etf_weight / weights.max())
    actual = risky_weights * exposure
    risk = float(np.sqrt(actual.to_numpy() @ covariance @ actual.to_numpy()))
    return ProfileAllocation(target, actual, float(1 - actual.sum()), risk)
