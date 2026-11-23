"""Unit-aware conditional exposures, robust variants and common-sample portfolio controls."""

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from ..econometrics import hac
from .inputs import FACTORS


def correlations(x, y):
    a = x - x.mean(axis=0)
    b = y - y.mean()
    denom = np.sqrt((a * a).sum(axis=0) * (b * b).sum())
    return np.divide(a.T @ b, denom, out=np.full(x.shape[1], np.nan), where=denom > 0)


def portfolio_paths(frame, weights):
    return pd.DataFrame(
        {
            name: frame[g.id].to_numpy() @ g.weight.to_numpy()
            for name, g in weights.groupby("option")
        },
        index=frame.index,
    )


def estimate(f, local, chf, cfg, parent):
    w, minimum = cfg["window"], cfg["minimum"]
    oil_limits = f.oil.loc[: cfg["calibration_end"]].quantile(cfg["quantiles"]).values
    central = f.iloc[-w:]
    variants = [
        (
            f"rolling_{offset}",
            f.iloc[len(f) - w - offset : len(f) - offset],
            chf,
            minimum,
        )
        for offset in cfg["rolling_offsets"]
    ]
    long_window = f.iloc[-2 * w :]
    trimmed = long_window.where(long_window.oil.between(*oil_limits))
    outside_crises = f.copy()
    for start, end in parent["events"].values():
        outside_crises.loc[(f.index > start) & (f.index <= end)] = np.nan
    variants.extend(
        [
            ("double_window", f.iloc[-2 * w :], chf, 2 * minimum),
            ("lag_one", f.shift(1).iloc[-w:], chf, minimum),
            ("reduced", central[["market", "fx", "oil"]], chf, minimum),
            ("trim_oil_tails", trimmed, chf, minimum),
            ("local_USD", central, local, minimum),
            ("history", f, chf, 2 * minimum),
            ("history_excluding_crises", outside_crises, chf, 2 * minimum),
        ]
    )
    rows = []
    for version, factors, returns, least in variants:
        values = returns.loc[factors.index].to_numpy()
        x = np.column_stack((np.ones(len(factors)), factors))
        valid = np.isfinite(x).all(axis=1)
        for j in np.flatnonzero(np.isfinite(values[valid]).sum(axis=0) >= least):
            y = values[:, j]
            fit = hac(x, y, least, parent["hac_lags"])
            if fit is None:
                continue
            coef, half, n = fit
            measured = valid & np.isfinite(y)
            p = s = np.full(factors.shape[1], np.nan)
            if version in ("rolling_0", "local_USD"):
                a, b = x[measured, 1:], y[measured]
                p = correlations(a, b)
                s = correlations(rankdata(a, axis=0), rankdata(b))
            for i, name in enumerate(factors.columns):
                rows.append(
                    (
                        returns.columns[j],
                        version,
                        name,
                        n,
                        coef[i + 1],
                        coef[i + 1] - half[i + 1],
                        coef[i + 1] + half[i + 1],
                        p[i],
                        s[i],
                    )
                )
    return pd.DataFrame(
        rows,
        columns=[
            "id",
            "variant",
            "factor",
            "n",
            "beta",
            "low",
            "high",
            "pearson",
            "spearman",
        ],
    )


def aggregation(f, chf, weights, cfg):
    x = f.iloc[-cfg["window"] :].to_numpy()
    result = []
    for name, g in weights.groupby("option"):
        y = chf[g.id].iloc[-len(x) :].to_numpy()
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y).all(axis=1)
        row = {
            "option": name,
            "common": int(valid.sum()),
            "max_beta_error": None,
            "max_corr_error": None,
        }
        if valid.sum() >= cfg["minimum"]:
            z = np.column_stack((np.ones(valid.sum()), x[valid]))
            individual, direct = [
                np.linalg.lstsq(z, target, rcond=None)[0]
                for target in (y[valid], y[valid] @ g.weight)
            ]
            err = np.max(np.abs(direct - individual @ g.weight))
            cov = np.cov(x[valid].T, y[valid].T)[: x.shape[1], x.shape[1] :]
            combined = y[valid] @ g.weight
            corr = (cov @ g.weight) / (
                np.std(x[valid], axis=0, ddof=1) * np.std(combined, ddof=1)
            )
            cerr = np.max(np.abs(corr - correlations(x[valid], combined)))
            assert err < 1e-9 and cerr < 1e-9
            row.update(max_beta_error=float(err), max_corr_error=float(cerr))
        result.append(row)
    return result


def bootstrap(f, y, cfg):
    """Paired moving blocks of contiguous exchange sessions with complete measurements."""
    x = np.column_stack((np.ones(len(f)), f))
    vals = np.asarray(y)
    ok = np.isfinite(x).all(axis=1) & np.isfinite(vals)
    k = cfg["block_sessions"]
    starts = np.flatnonzero(np.convolve(ok.astype(int), np.ones(k), "valid") == k)
    if len(starts) < 20 or ok.sum() < 200:
        return None
    rng = np.random.default_rng(cfg["seed"])
    out = []
    for _ in range(cfg["draws"]):
        ix = (
            rng.choice(starts, size=int(np.ceil(ok.sum() / k)))[:, None] + np.arange(k)
        ).ravel()[: ok.sum()]
        fit = np.linalg.lstsq(x[ix], vals[ix], rcond=None)[0]
        out.append(fit[1 + FACTORS.index("oil")] * 1000)
    lo, hi = np.quantile(out, [0.025, 0.975])
    return {
        "draws": len(out),
        "valid_blocks": len(starts),
        "observations": int(ok.sum()),
        "low_pct": lo,
        "high_pct": hi,
    }
