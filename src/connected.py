"""Connected Black–Litterman sleeve around the Balanced reference."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .balanced import fit_balanced
from .classic import classic_weights
from .optim import bl_posterior, tracking_error, vol


@dataclass(frozen=True)
class ConnectedPortfolio:
    weights: pd.Series
    reference: pd.Series
    annual_covariance: pd.DataFrame
    prior_excess_mean: pd.Series
    posterior_excess_mean: pd.Series
    tau: float | None
    annual_tracking_error: float


def connected_portfolio(reference: pd.Series, annual_covariance: pd.DataFrame, *,
                        reference_sharpe: float, p: pd.DataFrame | None = None,
                        q: pd.Series | None = None, omega: pd.DataFrame | None = None,
                        tau_max: float = .05, target_tracking_error: float = .03,
                        max_weight: float = 1.) -> ConnectedPortfolio:
    """Construct the long-only risky sleeve from an anchor and optional approved views."""
    if not np.isfinite(reference_sharpe) or reference_sharpe <= 0:
        raise ValueError("reference Sharpe must be positive and finite")
    if not np.isfinite(tau_max) or tau_max <= 0:
        raise ValueError("tau_max must be positive and finite")
    if not np.isfinite(target_tracking_error) or target_tracking_error <= 0:
        raise ValueError("target tracking error must be positive and finite")
    reference_vol = vol(reference, annual_covariance)
    if reference_vol <= 0 or (reference < 0).any() or not np.isclose(reference.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("reference must be long-only, fully invested, and have positive volatility")
    if not np.isfinite(max_weight) or not 1 / len(reference) <= max_weight <= 1:
        raise ValueError("infeasible maximum Connected weight")
    if reference.max() > max_weight + 1e-9:
        raise ValueError("reference weights must respect the Connected cap")
    prior = ((reference_sharpe / reference_vol) * (annual_covariance @ reference)).rename("excess_mean")

    if p is None and q is None and omega is None:
        return ConnectedPortfolio(reference.copy(), reference.copy(), annual_covariance, prior, prior.copy(), None, 0.)
    if p is None or q is None or omega is None:
        raise ValueError("provide P, Q, and Omega together")

    def optimize(tau: float):
        posterior = bl_posterior(prior, annual_covariance, p, q, omega, tau=tau)
        weights, method = classic_weights(posterior, annual_covariance, max_weight=max_weight)
        if method != "tangency":
            raise RuntimeError("Connected views yield no feasible positive tangency portfolio")
        return posterior, weights, tracking_error(weights, reference, annual_covariance)

    if len(p) == 0:
        posterior = bl_posterior(prior, annual_covariance, p, q, omega, tau=tau_max)
        return ConnectedPortfolio(reference.copy(), reference.copy(), annual_covariance, prior, posterior, None, 0.)

    tau = tau_max
    posterior, weights, error = optimize(tau)
    if error > target_tracking_error:
        def excess_tracking_error(value: float) -> float:
            if value == 0:
                return -target_tracking_error
            return optimize(value)[2] - target_tracking_error

        tau = brentq(excess_tracking_error, 0., tau_max, xtol=1e-12)
        posterior, weights, error = optimize(tau)
        if abs(error - target_tracking_error) > 1e-7:
            raise RuntimeError("Connected tracking error calibration did not reach the target")
    return ConnectedPortfolio(weights, reference.copy(), annual_covariance, prior, posterior, tau, error)


def fit_connected(returns: pd.DataFrame, *, decision_date: pd.Timestamp, reference_sharpe: float,
                  window: int = 756, p: pd.DataFrame | None = None, q: pd.Series | None = None,
                  omega: pd.DataFrame | None = None, tau_max: float = .05,
                  target_tracking_error: float = .03) -> ConnectedPortfolio:
    """Fit the ERC anchor through the decision close, then apply approved views."""
    anchor = fit_balanced(returns, decision_date=decision_date, window=window)
    return connected_portfolio(
        anchor.weights, anchor.annual_covariance, reference_sharpe=reference_sharpe,
        p=p, q=q, omega=omega, tau_max=tau_max, target_tracking_error=target_tracking_error,
    )
