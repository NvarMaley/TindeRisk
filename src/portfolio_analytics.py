"""Risk decompositions and realized benchmark-relative statistics."""

import numpy as np
import pandas as pd

from .optim import risk_contrib, vol


def risk_breakdown(weights: pd.Series, covariance: pd.DataFrame) -> pd.DataFrame:
    """Return signed contributions to volatility and their shares."""
    volatility = vol(weights, covariance)
    if volatility == 0:
        contribution = pd.Series(0., index=weights.index)
        shares = pd.Series(float("nan"), index=weights.index)
    else:
        contribution = risk_contrib(weights, covariance)
        shares = contribution / volatility
    return pd.DataFrame({"weight": weights, "risk_contribution": contribution, "risk_share": shares})


def _risky_weight_shares(weights: pd.Series) -> np.ndarray:
    values = weights.to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("concentration requires finite long-only weights")
    positive = values[values > 0]
    return positive / positive.sum() if positive.size else positive


def risky_weight_herfindahl(weights: pd.Series) -> float:
    """Measure concentration within the long-only risky sleeve, excluding cash."""
    shares = _risky_weight_shares(weights)
    return float((shares ** 2).sum()) if shares.size else float("nan")


def risky_weight_shannon(weights: pd.Series) -> float:
    """Return Shannon entropy in natural-log units, excluding cash."""
    shares = _risky_weight_shares(weights)
    return float(-shares @ np.log(shares)) if shares.size else float("nan")


def diversification_ratio(weights: pd.Series, covariance: pd.DataFrame) -> float:
    """Divide weighted standalone volatilities by portfolio volatility."""
    volatility = vol(weights, covariance)
    values = weights.to_numpy(dtype=float)
    if (values < 0).any():
        raise ValueError("diversification ratio requires long-only weights")
    standalone = np.sqrt(np.maximum(np.diag(covariance), 0.))
    return float(values @ standalone / volatility) if volatility > 0 else float("nan")


def expected_shortfall_loss(returns: pd.Series, confidence: float = .95) -> float:
    """Return the empirical average loss over the worst probability mass."""
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between zero and one")
    values = returns.to_numpy(dtype=float, na_value=np.nan)
    if not values.size or not np.isfinite(values).all():
        raise ValueError("expected shortfall requires nonempty finite returns")
    ordered = np.sort(values)
    mass = (1 - confidence) * values.size
    count = int(mass)
    boundary = ordered[min(count, values.size - 1)]
    return -float((ordered[:count].sum() + (mass - count) * boundary) / mass)


def information_ratio(returns: pd.Series, benchmark: pd.Series, periods_per_year: int = 252) -> float:
    """Annualize average realized active return divided by active volatility."""
    dates = returns.index
    if (not isinstance(dates, pd.DatetimeIndex) or dates.hasnans or len(dates) < 2
            or not dates.equals(benchmark.index) or not dates.is_unique or not dates.is_monotonic_increasing):
        raise ValueError("information ratio requires aligned, ordered session returns")
    values = returns.to_numpy(dtype=float, na_value=np.nan)
    reference = benchmark.to_numpy(dtype=float, na_value=np.nan)
    if (not np.isfinite(values).all() or not np.isfinite(reference).all()
            or not np.isfinite(periods_per_year) or periods_per_year <= 0):
        raise ValueError("information ratio requires finite returns and positive annualization")
    active = values - reference
    if np.ptp(active) == 0:
        return float("nan")
    return float(np.sqrt(periods_per_year) * active.mean() / active.std(ddof=1))
