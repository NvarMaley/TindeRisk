"""Estimate Black–Litterman view uncertainty from historical validation errors."""

import numpy as np
import pandas as pd

from .view_returns import SESSIONS_PER_YEAR


def estimate_omega(
    active_p: pd.DataFrame,
    annual_covariance: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    tau: float,
    error_multiplier: float = 1.0,
) -> pd.DataFrame:
    """Return labelled, diagonal annualized uncertainty for active Q views.

    Each diagonal entry uses the frozen training forecast's validation MSE
    and a floor equal to the prior uncertainty of that same spread.
    """
    if not np.isfinite(tau) or tau <= 0 or not np.isfinite(error_multiplier) or error_multiplier <= 0:
        raise ValueError("Tau and the validation-error multiplier must be positive and finite")
    views = active_p.index
    if len(views) == 0:
        return pd.DataFrame(index=views, columns=views, dtype=float)
    assets = active_p.columns
    if views.has_duplicates or assets.has_duplicates or diagnostics.index.has_duplicates:
        raise ValueError("Omega requires unique asset and view labels")
    if (annual_covariance.index.has_duplicates or annual_covariance.columns.has_duplicates
            or not assets.isin(annual_covariance.index).all()
            or not assets.isin(annual_covariance.columns).all()):
        raise ValueError("Annual covariance must cover the assets in P")

    if not {"status", "validation_mse"}.issubset(diagnostics.columns):
        raise ValueError("Each active view requires an observed validation MSE")
    evidence = diagnostics.reindex(views)
    daily_mse = evidence["validation_mse"].to_numpy(dtype=float, na_value=np.nan)
    if (not evidence["status"].eq("active").fillna(False).all()
            or not np.isfinite(daily_mse).all() or (daily_mse < 0).any()):
        raise ValueError("Each active view requires an observed validation MSE")

    p = active_p.to_numpy(dtype=float)
    sigma = annual_covariance.loc[assets, assets].to_numpy(dtype=float)
    if not np.isfinite(p).all() or not np.isfinite(sigma).all() or not np.allclose(sigma, sigma.T):
        raise ValueError("P and its aligned symmetric covariance must be finite")
    prior_variances = tau * np.diag(p @ sigma @ p.T)
    variance = np.maximum(prior_variances, error_multiplier * daily_mse * SESSIONS_PER_YEAR**2)
    if not np.isfinite(variance).all() or (prior_variances <= 0).any():
        raise ValueError("Each active view must have positive, finite prior variance")
    return pd.DataFrame(np.diag(variance), index=views, columns=views)
