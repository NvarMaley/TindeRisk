"""Historical-risk estimators. Return series retain the original venue-session grid."""

import math

import numpy as np
import pandas as pd
from scipy.special import xlogy
from scipy.stats import binomtest, chi2

LEVELS = (0.95, 0.99)
WEIGHTS = np.full(3, 1 / 3)
ASSETS = ["SPY", "IEF", "GLD"]


def historical_tail(losses, level):
    x = np.asarray(losses, dtype=float)
    ordered = np.sort(x[np.isfinite(x)])[::-1]
    n = len(ordered)
    if not n or not 0 < level < 1:
        raise ValueError("A valid confidence level and observed losses are required")
    mass = round(n * (1 - level), 12)
    full = math.floor(mass)
    fraction = mass - full
    var = ordered[full]
    es = (ordered[:full].sum() + fraction * var) / mass
    return float(var), float(es)


def block_indices(n, length, generator):
    """Overlapping moving blocks of venue sessions, never joining gaps before sampling."""
    size = min(length, n)
    starts = generator.integers(0, n - size + 1, size=math.ceil(n / size))
    return (starts[:, None] + np.arange(size)).ravel()[:n]


def block_estimates(array, statistic, size, seed=4102, draws=2000):
    rng = np.random.default_rng(seed)
    estimates = np.array(
        [statistic(array[block_indices(len(array), size, rng)]) for _ in range(draws)]
    )
    return np.nanquantile(estimates, [0.025, 0.975], axis=0)


def underwater(wealth):
    """Preserve missing marks and avoid silently restarting the high-water mark."""
    observed = wealth.dropna()
    if observed.empty or observed.iloc[0] <= 0 or (observed < 0).any():
        raise ValueError("A positive initial mark and nonnegative wealth are required")
    peak = observed.index[0]
    trough = peak
    active = False
    episodes = []
    dd = wealth / wealth.cummax() - 1
    age = pd.Series(np.nan, index=wealth.index)
    for day, value in observed.items():
        if value >= observed.loc[peak]:
            if active:
                episodes.append(
                    (peak, trough, day, -dd.at[trough], (day - peak).days, False)
                )
            peak = trough = day
            active = False
        else:
            active = True
            if value < observed.loc[trough]:
                trough = day
        age.loc[day] = (day - peak).days
    if active:
        episodes.append(
            (
                peak,
                trough,
                pd.NaT,
                -dd.at[trough],
                (observed.index[-1] - peak).days,
                True,
            )
        )
    return (
        dd,
        age,
        pd.DataFrame(
            episodes,
            columns=["peak", "trough", "recovery", "depth", "duration_days", "ongoing"],
        ),
    )


def attribution(cov, weights):
    cov = np.asarray(cov, dtype=float)
    symmetric = np.allclose(cov, cov.T, atol=1e-14, rtol=1e-12)
    eig = np.linalg.eigvalsh((cov + cov.T) / 2)
    scale = max(float(np.max(np.abs(eig))), 1e-16)
    variance = float(weights @ cov @ weights)
    cond = float(np.linalg.cond(cov)) if eig[0] > 0 else np.inf
    status = (
        "invalid covariance"
        if not symmetric or eig[0] < -scale * 1e-10
        else "near-zero portfolio volatility"
        if variance <= 1e-16
        else "singular or ill-conditioned"
        if cond > 1e10
        else "ok"
    )
    stats = {
        "status": status,
        "symmetric": bool(symmetric),
        "eigenvalues": eig.tolist(),
        "condition": cond,
        "variance": variance,
        "effective_holdings": 1 / (weights @ weights),
    }
    if status in ("invalid covariance", "near-zero portfolio volatility"):
        return stats, None
    sd = math.sqrt(variance)
    marginal = cov @ weights / sd
    component = weights * marginal
    var_component = weights * (cov @ weights)
    np.testing.assert_allclose(
        [sum(component), sum(var_component)], [sd, variance], rtol=1e-10, atol=1e-14
    )
    stats.update(
        volatility=sd,
        diversification_ratio=weights @ np.sqrt(np.maximum(np.diag(cov), 0)) / sd,
    )
    return stats, {
        "marginal_vol": marginal,
        "vol_component": component,
        "variance_component": var_component,
        "risk_share": component / sd,
    }


def horizon_risk(returns, horizon=21):
    log = np.log1p(returns)
    centered = log - log.mean()
    gamma0 = (centered**2).mean()
    lags = [(centered * centered.shift(k)).dropna() for k in range(1, horizon)]
    adjusted = horizon * gamma0 + 2 * sum(
        (horizon - k) * p.mean() for k, p in enumerate(lags, 1)
    )
    compounded = np.expm1(log.rolling(horizon, min_periods=horizon).sum().dropna())
    return {
        "horizon": horizon,
        "iid_log_sd": math.sqrt(horizon * gamma0),
        "autocov_log_sd": math.sqrt(adjusted) if adjusted >= 0 else np.nan,
        "min_lag_pairs": min(map(len, lags)),
        "compounded_simple_sd": compounded.std(),
        "complete_paths": len(compounded),
    }


def forecasts(returns, origins, level):
    """One-step forecast at t from exactly the preceding 252 calendar rows."""
    alpha = 1 - level
    rows = []
    for day in origins:
        i = returns.index.get_loc(day)
        history = -returns.iloc[max(0, i - 252) : i].dropna()
        var, es = (
            historical_tail(history, level)
            if i >= 252 and len(history) >= 240
            else (np.nan, np.nan)
        )
        loss = -returns.iloc[i]
        valid = np.isfinite(loss) and np.isfinite(var)
        hit = float(loss > var) if valid else np.nan
        score = (
            math.log(es) - 1 + var / es + max(loss - var, 0) / (alpha * es)
            if valid and es > 0
            else np.nan
        )
        rows.append(
            (
                day,
                returns.index[i - 1] if i else pd.NaT,
                len(history),
                level,
                var,
                es,
                loss,
                hit,
                score,
            )
        )
    return pd.DataFrame(
        rows,
        columns=[
            "session",
            "cutoff_session",
            "history_n",
            "level",
            "var",
            "es",
            "loss",
            "hit",
            "fz0",
        ],
    )


def coverage(ledger, level):
    h = ledger.hit.to_numpy()
    n = np.isfinite(h).sum()
    k = int(np.nansum(h))
    a = round(1 - level, 12)
    before, after = h[:-1], h[1:]
    t = np.array(
        [[np.sum((before == i) & (after == j)) for j in (0, 1)] for i in (0, 1)]
    )

    def loglik(misses, hits, p):
        return xlogy(misses, 1 - p) + xlogy(hits, p)

    exact = binomtest(k, n, a) if n else None
    lo, hi = exact.proportion_ci() if exact else (np.nan, np.nan)
    uc = 2 * (loglik(n - k, k, k / n) - loglik(n - k, k, a)) if n else np.nan
    totals = t.sum(axis=1)
    prob = t[:, 1].sum() / t.sum() if t.sum() else np.nan
    expected = np.outer(totals, [1 - prob, prob])
    enough_uc = min(n * a, n * (1 - a)) >= 5 and 0 < k < n
    enough_ind = expected.min() >= 5 and (t > 0).all()
    ind = np.nan
    if enough_ind:
        alt = sum(loglik(row[0], row[1], row[1] / row.sum()) for row in t)
        ind = max(0, 2 * (alt - loglik(t[:, 0].sum(), t[:, 1].sum(), prob)))
    runs = int(np.sum((h == 1) & ~np.r_[False, h[:-1] == 1])) if len(h) else 0

    def hit_rate(block):
        observed = block[np.isfinite(block)]
        return np.nanmean(block) if len(observed) else np.nan

    intervals = block_estimates(h, hit_rate, 5) if n else (np.nan, np.nan)
    return {
        "level": level,
        "scheduled": len(h),
        "forecasts": int(ledger["var"].notna().sum()),
        "verified": int(n),
        "expected": n * a,
        "breaches": k,
        "ties": int((ledger.loss == ledger["var"]).sum()),
        "rate": k / n if n else np.nan,
        "breach_runs": runs,
        "n00": t[0, 0],
        "n01": t[0, 1],
        "n10": t[1, 0],
        "n11": t[1, 1],
        "binomial_p": exact.pvalue if exact else np.nan,
        "exact_low": lo,
        "exact_high": hi,
        "block_low": intervals[0],
        "block_high": intervals[1],
        "kupiec_p": chi2.sf(max(0, uc), 1) if enough_uc else np.nan,
        "independence_p": chi2.sf(ind, 1),
        "conditional_p": chi2.sf(uc + ind, 2) if enough_uc and enough_ind else np.nan,
        "transition_status": "estimable"
        if enough_ind
        else "sparse; report transitions only",
        "mean_fz0": ledger.fz0.mean(),
    }
