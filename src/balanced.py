"""Balanced risky sleeve fitted by equal risk contribution."""

from dataclasses import dataclass

import pandas as pd

from .estimation import ledoit_wolf_constant_corr, trailing_returns_at_close
from .optim import erc


@dataclass(frozen=True)
class BalancedPortfolio:
    weights: pd.Series
    annual_covariance: pd.DataFrame


def fit_balanced(returns: pd.DataFrame, *, decision_date: pd.Timestamp,
                 window: int = 756) -> BalancedPortfolio:
    """Fit the fully invested ERC sleeve before client-specific constraints."""
    history = trailing_returns_at_close(returns, decision_date, window)
    covariance, _ = ledoit_wolf_constant_corr(history)
    return BalancedPortfolio(erc(covariance), covariance)
