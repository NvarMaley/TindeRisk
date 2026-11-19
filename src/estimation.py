"""Validated daily-return covariance estimators; outputs are annualized."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


def trailing_returns_at_close(returns: pd.DataFrame, decision_date: pd.Timestamp,
                              window: int) -> pd.DataFrame:
    """Select the exact trailing sample, including the observed decision close."""
    if not isinstance(window, int) or isinstance(window, bool) or window < 2:
        raise ValueError("window must be an integer of at least 2")
    dates = returns.index
    if (not isinstance(dates, pd.DatetimeIndex) or dates.hasnans
            or not dates.is_unique or not dates.is_monotonic_increasing):
        raise ValueError("risky returns require sorted and unique dates")
    date = pd.Timestamp(decision_date)
    if date not in dates:
        raise ValueError("decision close must belong to returns")
    end = dates.get_loc(date) + 1
    if end < window:
        raise ValueError("insufficient trailing history")
    return returns.iloc[end - window:end]


def validate_returns(returns: pd.DataFrame, annualize: int = 252) -> None:
    """Require a complete ordered panel and nonconstant asset returns."""
    if len(returns) < 2 or returns.shape[1] < 2:
        raise ValueError("need at least 2 observations and 2 assets")
    if not np.isfinite(annualize) or annualize <= 0:
        raise ValueError("annualization must be positive and finite")
    if not isinstance(returns.index, pd.DatetimeIndex) or returns.index.hasnans:
        raise ValueError("returns require nonmissing datetime dates")
    if not returns.index.is_unique or not returns.index.is_monotonic_increasing:
        raise ValueError("returns require sorted unique dates")
    if returns.columns.has_duplicates:
        raise ValueError("asset columns must be unique")
    values = returns.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("returns must be finite and strictly above -1")
    if (returns.nunique() < 2).any():
        raise ValueError("each asset must have nonzero variance")


def sample_cov(returns: pd.DataFrame, annualize: int = 252) -> pd.DataFrame:
    """Unbiased sample covariance (ddof=1), annualized."""
    validate_returns(returns, annualize)
    return returns.cov() * annualize


def ledoit_wolf_constant_corr(returns: pd.DataFrame, annualize: int = 252) -> tuple[pd.DataFrame, float]:
    """Ledoit–Wolf constant-correlation target (LN3), with sample-scale output.

    Moment estimates use denominator n as in Ledoit & Wolf (2004), Appendix B.
    After estimating shrinkage, scale the whole matrix by n/(n-1) so all
    estimators have the same ddof=1 convention. The diagonal is thus identical
    to the unbiased sample diagonal. This differs from shrinking toward identity.
    """
    validate_returns(returns, annualize)
    X = returns.to_numpy(dtype=float)
    n, p = X.shape
    X = X - X.mean(axis=0)
    S = X.T @ X / n
    var = np.diag(S)
    sd = np.sqrt(var)
    corr = S / np.outer(sd, sd)
    r_bar = (corr.sum() - p) / (p * (p - 1))
    target = r_bar * np.outer(sd, sd)
    np.fill_diagonal(target, var)
    X2 = X**2
    pi_mat = X2.T @ X2 / n - S**2
    theta = (X**3).T @ X / n - var[:, None] * S
    np.fill_diagonal(theta, 0.)
    rho = np.trace(pi_mat) + r_bar * (np.outer(1 / sd, sd) * theta).sum()
    gamma = np.linalg.norm(S - target, "fro")**2
    # With two assets (or exactly constant correlations), S already equals F.
    if gamma <= np.finfo(float).eps * np.linalg.norm(S, "fro")**2:
        delta = 1.
    else:
        delta = float(np.clip((pi_mat.sum() - rho) / (n * gamma), 0., 1.))
    sigma = (delta * target + (1 - delta) * S) * (n / (n - 1)) * annualize
    return pd.DataFrame(sigma, index=returns.columns, columns=returns.columns), delta


def rolling_covariances(returns: pd.DataFrame, decision_dates: pd.DatetimeIndex,
                        window: int = 756, annualize: int = 252):
    """Estimate at the close on explicit dates, using exactly window past rows.

    Includes the decision-session close; usable only AFTER that close. There is
    no trading or strategy performance simulation here. SPY is excluded by the
    caller when it is a benchmark rather than an investable asset.
    """
    validate_returns(returns, annualize)
    if not isinstance(window, int) or window < 2:
        raise ValueError("window must be an integer of at least 2")
    dates = pd.DatetimeIndex(decision_dates)
    if dates.empty or dates.hasnans or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("decision dates must be nonempty, sorted and unique")
    if not dates.isin(returns.index).all():
        raise ValueError("decision dates must belong to the return panel")
    matrices, diagnostics = [], []
    for date in dates:
        end = returns.index.get_loc(date) + 1
        if end < window:
            raise ValueError("insufficient strictly historical estimation data")
        panel = returns.iloc[end-window:end]
        cc, delta = ledoit_wolf_constant_corr(panel, annualize)
        identity = LedoitWolf().fit(panel.to_numpy())
        values = {"sample": sample_cov(panel, annualize),
                  "lw_constcorr": cc,
                  "lw_identity": pd.DataFrame(identity.covariance_ * window / (window-1) * annualize,
                                               index=panel.columns, columns=panel.columns)}
        for estimator, cov in values.items():
            block = cov.copy()
            block.index.name = "asset"
            matrices.append(pd.concat({(date, estimator): block}, names=["date", "estimator"]))
            eigenvalues = np.linalg.eigvalsh(cov)
            diagnostics.append({"date": date, "estimator": estimator,
                "window_start": panel.index[0], "window_end": panel.index[-1],
                "observations": len(panel), "condition_number": np.linalg.cond(cov),
                "min_eigenvalue": eigenvalues[0], "max_eigenvalue": eigenvalues[-1],
                "shrinkage": np.nan if estimator == "sample" else (
                    delta if estimator == "lw_constcorr" else identity.shrinkage_)})
    return (pd.concat(matrices).sort_index(level=["date", "estimator"], sort_remaining=False),
            pd.DataFrame(diagnostics).set_index(["date", "estimator"]).sort_index())
