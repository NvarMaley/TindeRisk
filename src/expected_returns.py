"""Raf's regularized Bayes–Stein-style excess-mean shrinkage, step 2.3.

This is a documented regularized variant, not a claim of exact finite-sample
Jorion optimality or of a lower expected loss/return. Inputs share one frequency.
"""

import numpy as np
import pandas as pd


def shrink_expected_mean(mean: pd.Series, covariance: pd.DataFrame,
                         observations: int) -> tuple[pd.Series, dict]:
    """Shrink historical excess means toward their covariance-metric GMV mean.

    Use DAILY means and DAILY covariance together with the number of daily
    observations. Annualize only the final output, never the inputs to this
    daily-frequency formula. Return values have the same units as mean.
    Intensity = (p+2)/(p+2 + T*(mean-target)' inv(cov) (mean-target)).
    Covariance may be regularized; the GMV reference here is unconstrained
    and is not a tradable long-only strategy or the approved BL ERC anchor.
    """
    if not isinstance(observations, (int, np.integer)) or isinstance(observations, bool) or observations < 2:
        raise ValueError("observations must be an integer of at least 2")
    if len(mean) < 2 or mean.index.has_duplicates:
        raise ValueError("need at least two uniquely labelled asset means")
    if not covariance.index.equals(mean.index) or not covariance.columns.equals(mean.index):
        raise ValueError("mean and covariance labels must match exactly")
    values = mean.to_numpy(dtype=float)
    matrix = covariance.to_numpy(dtype=float)
    if not np.isfinite(values).all() or not np.isfinite(matrix).all():
        raise ValueError("mean and covariance must be finite")
    if not np.allclose(matrix, matrix.T, rtol=1e-10, atol=1e-14):
        raise ValueError("covariance must be symmetric")
    try:
        np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as error:
        raise ValueError("covariance must be positive definite") from error
    ones = np.ones(len(mean))
    inv_ones = np.linalg.solve(matrix, ones)
    target = float(inv_ones @ values / inv_ones.sum())
    deviation = values - target
    distance = max(0., float(deviation @ np.linalg.solve(matrix, deviation)))
    intensity = float((len(mean) + 2) / (len(mean) + 2 + observations * distance))
    shrunk = (1 - intensity) * values + intensity * target
    return pd.Series(shrunk, index=mean.index, name="shrunk_excess_mean"), {
        "shrinkage": intensity, "target": target,
        "mahalanobis_distance_squared": distance, "observations": int(observations)}


def rolling_expected_returns(returns: pd.DataFrame, excess_returns: pd.DataFrame,
                             decision_dates: pd.DatetimeIndex, window: int = 756,
                             annualize: int = 252):
    """Trailing-close estimates, using asset risk and aligned excess means.

    Covariance uses simple asset returns, consistent with step 2.2; excess
    means use the existing DTB3 proxy. This explicitly differs from estimating
    covariance of rate-subtracted returns. Outputs are annual arithmetic excess
    means, never CAGRs or forecasts displayed as promised client returns.
    """
    from .estimation import ledoit_wolf_constant_corr, validate_returns

    validate_returns(returns, annualize)
    if not returns.index.equals(excess_returns.index) or not returns.columns.equals(excess_returns.columns):
        raise ValueError("returns and excess returns must have exactly matching dates and assets")
    if not np.isfinite(excess_returns.to_numpy(dtype=float)).all():
        raise ValueError("excess returns must be complete and finite")
    if not isinstance(window, int) or isinstance(window, bool) or window < 2:
        raise ValueError("window must be an integer of at least 2")
    dates = pd.DatetimeIndex(decision_dates)
    if dates.empty or dates.hasnans or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("decision dates must be nonempty, sorted and unique")
    if not dates.isin(returns.index).all():
        raise ValueError("decision dates must belong to returns")
    raw_rows, shrunk_rows, diagnostics = [], [], []
    for date in dates:
        end = returns.index.get_loc(date) + 1
        if end < window:
            raise ValueError("insufficient trailing history")
        daily = returns.iloc[end-window:end]
        excess = excess_returns.iloc[end-window:end]
        cov, cov_intensity = ledoit_wolf_constant_corr(daily, annualize=1)
        raw = excess.mean()
        shrunk, info = shrink_expected_mean(raw, cov, len(daily))
        raw_rows.append(raw.to_numpy() * annualize)
        shrunk_rows.append(shrunk.to_numpy() * annualize)
        diagnostics.append({"date": date, "window_start": daily.index[0],
            "window_end": daily.index[-1], "observations": len(daily),
            "shrinkage": info["shrinkage"], "covariance_shrinkage": cov_intensity,
            "annual_target_excess_mean": info["target"] * annualize,
            "mahalanobis_distance_squared_daily": info["mahalanobis_distance_squared"],
            "raw_cross_sectional_std": raw.std(ddof=1) * annualize,
            "shrunk_cross_sectional_std": shrunk.std(ddof=1) * annualize})
    dates.name = "date"
    return (pd.DataFrame(shrunk_rows, index=dates, columns=returns.columns),
            pd.DataFrame(raw_rows, index=dates, columns=returns.columns),
            pd.DataFrame(diagnostics).set_index("date"))
