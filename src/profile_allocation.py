"""Scale a supplied risky portfolio to the effective profile target."""

from dataclasses import dataclass
import pandas as pd

from .optim import target_vol
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
    target = risk_target(risk_aversion, reference_sharpe, capacity)
    allocation = target_vol(risky_weights, annual_covariance, target.effective,
                            max_risky_exposure=max_risky_exposure, max_etf_weight=max_etf_weight)
    return ProfileAllocation(target, allocation.risky_weights, allocation.cash_weight,
                             allocation.achieved_volatility)
