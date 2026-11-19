"""Scale a supplied risky portfolio to an effective profile or band target."""

from dataclasses import dataclass
from math import isfinite

import pandas as pd

from .optim import TargetAllocation, target_vol
from .profiling import RiskBand, RiskTarget, risk_target


@dataclass(frozen=True)
class ProfileAllocation:
    target: RiskTarget
    risky_weights: pd.Series
    cash_weight: float
    achieved_volatility: float


@dataclass(frozen=True)
class BandAllocation:
    band: RiskBand
    allocation: TargetAllocation

    @property
    def risky_exposure(self) -> float:
        return 1. - self.allocation.cash_weight

    @property
    def target_shortfall(self) -> float:
        return max(0., self.band.reference_volatility - self.allocation.achieved_volatility)


def allocate_for_risk_band(risky_weights: pd.Series, annual_covariance: pd.DataFrame, band: RiskBand, *,
                           allow_leverage: bool = False, leverage_limit: float = 1.5) -> BandAllocation:
    """Scale a strategy sleeve toward a band's reference before personal constraints."""
    if not isinstance(allow_leverage, bool):
        raise ValueError("leverage requires an explicit boolean opt-in")
    if not isfinite(leverage_limit) or leverage_limit < 1:
        raise ValueError("leverage limit must be finite and at least 1")
    if not isfinite(band.reference_volatility) or band.reference_volatility <= 0:
        raise ValueError("reference volatility must be positive and finite")
    limit = leverage_limit if allow_leverage else 1.
    allocation = target_vol(risky_weights, annual_covariance, band.reference_volatility,
                            max_risky_exposure=limit, max_etf_weight=None)
    return BandAllocation(band, allocation)


def allocate_for_profile(risky_weights: pd.Series, annual_covariance: pd.DataFrame, *,
                         risk_aversion: float, reference_sharpe: float, capacity: float,
                         max_risky_exposure: float = 1., max_etf_weight: float = 1.) -> ProfileAllocation:
    """Mix the risky sleeve and cash, then measure risk on the actual weights."""
    target = risk_target(risk_aversion, reference_sharpe, capacity)
    allocation = target_vol(risky_weights, annual_covariance, target.effective,
                            max_risky_exposure=max_risky_exposure, max_etf_weight=max_etf_weight)
    return ProfileAllocation(target, allocation.risky_weights, allocation.cash_weight,
                             allocation.achieved_volatility)
