"""Chameleon risky sleeve using dated macro state probabilities."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .estimation import ledoit_wolf_constant_corr, trailing_returns_at_close
from .optim import risk_budget


@dataclass(frozen=True)
class ChameleonPortfolio:
    weights: pd.Series
    annual_covariance: pd.DataFrame
    group_budgets: pd.Series
    asset_budgets: pd.Series
    regime_observation: pd.Timestamp


def _latest_available_regime(filtered: pd.DataFrame, decision: pd.Timestamp) -> pd.Series:
    observations = filtered.index
    available = pd.DatetimeIndex(filtered["available_date"])
    if (not isinstance(observations, pd.DatetimeIndex) or observations.tz is not None
            or observations.hasnans or not observations.is_monotonic_increasing
            or not observations.is_unique or available.tz is not None or available.hasnans
            or not available.is_unique or not available.is_monotonic_increasing
            or (available <= observations).any()):
        raise ValueError("regime data require ordered unique observations and later availability dates")
    usable = filtered.loc[available <= decision]
    if usable.empty:
        raise ValueError("no filtered regime is available by the decision close")
    return usable.iloc[-1]


def mix_regime_budgets(probabilities: pd.Series, state_budgets: pd.DataFrame) -> pd.Series:
    """Average group risk shares using a single filtered probability vector."""
    if (state_budgets.empty or not state_budgets.index.is_unique
            or not state_budgets.columns.is_unique or state_budgets.columns.hasnans
            or state_budgets.index.hasnans or not probabilities.index.equals(state_budgets.index)):
        raise ValueError("each probability requires a unique matching state and budget row")
    p = probabilities.to_numpy(dtype=float)
    budgets = state_budgets.to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("state probabilities must be nonnegative and sum to one")
    if (not np.isfinite(budgets).all() or (budgets <= 0).any()
            or not np.allclose(budgets.sum(axis=1), 1, atol=1e-10, rtol=0)):
        raise ValueError("group risk budgets must be positive and sum to one per state")
    return pd.Series(p @ budgets, index=state_budgets.columns, name="target_risk_share")


def fit_chameleon(returns: pd.DataFrame, filtered: pd.DataFrame, state_budgets: pd.DataFrame,
                  asset_groups: pd.Series, *, decision_date: pd.Timestamp,
                  window: int = 756) -> ChameleonPortfolio:
    """Allocate to risk budgets available at the specified decision close."""
    decision = pd.Timestamp(decision_date)
    history = trailing_returns_at_close(returns, decision, window)
    regime = _latest_available_regime(filtered, decision)
    probabilities = regime.reindex(state_budgets.index)
    group_budgets = mix_regime_budgets(probabilities, state_budgets)
    if (not asset_groups.index.equals(returns.columns) or asset_groups.isna().any()
            or set(asset_groups) != set(group_budgets.index)):
        raise ValueError("each asset needs one group and each budget group needs at least one asset")
    group_sizes = asset_groups.value_counts()
    budgets = asset_groups.map(group_budgets) / asset_groups.map(group_sizes)
    covariance, _ = ledoit_wolf_constant_corr(history)
    weights = risk_budget(covariance, budgets)
    return ChameleonPortfolio(weights, covariance, group_budgets, budgets, regime.name)
