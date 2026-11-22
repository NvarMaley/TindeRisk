"""Estimators for the preregistered chapter 5 robustness extension."""

import numpy as np
from scipy.optimize import minimize
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def rescaled_covariance(long, short):
    corr = np.corrcoef(long, rowvar=False)
    n = len(corr)
    rho = corr[np.triu_indices(n, 1)].mean()
    target = np.full_like(corr, rho)
    np.fill_diagonal(target, 1.0)
    sd = np.std(short, axis=0, ddof=1)
    return np.outer(sd, sd) * (corr + target) / 2


def filtered_path(squares, long_run, alpha, persistence):
    """Variance immediately before each observation and after the final observation."""
    h = long_run
    omega = (1 - persistence) * long_run
    path = np.empty(len(squares) + 1)
    for i, x in enumerate(squares):
        path[i] = h
        h = omega + persistence * h + (alpha * (x - h) if x >= 0 else 0.0)
    path[-1] = h
    return path


def gap_forecast(returns, horizon):
    # Negative sentinel is confined to squared observations and incurs no likelihood term.
    squared = np.asarray(returns) ** 2
    obs = np.isfinite(squared)
    n = obs.sum()
    if len(squared) != 756 or n < 719:
        return np.nan, {"status": "insufficient coverage", "observed": n}
    mean = squared[obs].mean()
    if mean <= 0:
        return np.nan, {"status": "zero variance", "observed": n}
    x = np.where(obs, squared / mean, -1.0)

    def objective(params):
        h = filtered_path(x, 1.0, *params)[:-1][obs]
        return np.mean(np.log(h) + x[obs] / h)

    fit = minimize(
        objective, [0.06, 0.94], bounds=[(0, 0.35), (0.5, 0.995)], method="L-BFGS-B"
    )
    if not fit.success:
        return np.nan, {"status": "failed fit", "observed": n}
    a, rho = fit.x
    last = filtered_path(x, 1.0, a, rho)[-1]
    pred = mean * np.sum(1 + (last - 1) * rho ** np.arange(horizon))
    return pred, {
        "status": "fit",
        "observed": n,
        "alpha": a,
        "persistence": rho,
        "at_bound": bool(min(a, 0.35 - a, rho - 0.5, 0.995 - rho) < 1e-5),
    }


def mean_forecast(X, y, x, study):
    valid = np.isfinite(y) & np.isfinite(X).all(axis=1)
    X, y = X[valid], y[valid]
    if len(y) < 36 or not np.isfinite(x).all():
        return np.nan
    if study == "H03":
        scaler = StandardScaler().fit(X)
        reg = Ridge(alpha=12.0).fit(scaler.transform(X), y)
        return reg.predict(scaler.transform(x[None, :]))[0]
    centered = X[:, 0] - X[:, 0].mean()
    slope = (
        max(0, centered @ (y - y.mean()) / (centered @ centered))
        if centered @ centered > 0
        else 0.0
    )
    return max(0, y.mean() + 0.5 * slope * (x[0] - X[:, 0].mean()))
