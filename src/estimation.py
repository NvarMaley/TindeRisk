"""Covariance estimators used by the notebook, the backtest and the application."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sample_cov(returns: pd.DataFrame, annualize: int = 252) -> pd.DataFrame:
    """Unbiased sample covariance, annualised."""
    return returns.cov() * annualize


def ledoit_wolf_constant_corr(returns: pd.DataFrame, annualize: int = 252) -> tuple[pd.DataFrame, float]:
    """Ledoit & Wolf (2004) shrinkage towards the constant-correlation model (QARM II, LN3).

    Sigma_hat = delta * F + (1 - delta) * S, where F keeps each asset's own variance and
    sets every correlation to the average sample correlation. The optimal delta follows
    "Honey, I Shrunk the Sample Covariance Matrix" (Appendix B of the LN3 slides).

    Returns the annualised covariance matrix and the shrinkage intensity delta in [0, 1].
    """
    X = returns.to_numpy(dtype=float)
    t, n = X.shape
    if t < 2 or n < 2:
        raise ValueError("need at least 2 observations and 2 assets")
    X = X - X.mean(axis=0)
    T = t - 1  # effective sample size after demeaning

    S = X.T @ X / T
    var = np.diag(S)
    sd = np.sqrt(var)
    corr = S / np.outer(sd, sd)
    r_bar = (corr.sum() - n) / (n * (n - 1))

    F = r_bar * np.outer(sd, sd)
    np.fill_diagonal(F, var)

    # pi: sum of asymptotic variances of the entries of S
    X2 = X ** 2
    pi_mat = X2.T @ X2 / T - S ** 2
    pi_hat = pi_mat.sum()

    # rho: sum of asymptotic covariances between entries of F and S
    theta = (X ** 3).T @ X / T - var[:, None] * S
    np.fill_diagonal(theta, 0.0)
    rho_hat = np.trace(pi_mat) + r_bar * (np.outer(1 / sd, sd) * theta).sum()

    # gamma: misspecification of the target
    gamma_hat = np.linalg.norm(S - F, "fro") ** 2

    kappa = (pi_hat - rho_hat) / gamma_hat
    delta = float(np.clip(kappa / T, 0.0, 1.0))

    sigma = delta * F + (1 - delta) * S
    cols = returns.columns
    return pd.DataFrame(sigma * annualize, cols, cols), delta
