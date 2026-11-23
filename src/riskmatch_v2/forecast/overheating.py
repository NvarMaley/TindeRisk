"""Right-tailed rolling ADF(0) diagnostics on a predeclared monthly basket."""

import numpy as np
import pandas as pd


def statistics(paths, minimum):
    """SADF, GSADF and end-date BSADF. Each regression includes an intercept."""
    y = np.diff(paths, axis=1)
    x = paths[:, :-1]
    sums = [
        np.pad(np.cumsum(a, axis=1), ((0, 0), (1, 0)))
        for a in (x, y, x * x, x * y, y * y)
    ]
    gs = np.full(len(paths), -np.inf)
    sad = gs.copy()
    for end in range(minimum - 1, paths.shape[1]):
        left = np.arange(0, end - minimum + 2)
        n = end - left
        sx, sy, sxx, sxy, syy = [s[:, end, None] - s[:, left] for s in sums]
        xx = np.maximum(sxx - sx * sx / n, 1e-16)
        xy = sxy - sx * sy / n
        rss = np.maximum(syy - sy * sy / n - xy * xy / xx, 1e-16)
        t = xy / np.sqrt(xx * rss / (n - 2))
        bs = t.max(axis=1)
        gs = np.maximum(gs, bs)
        sad = np.maximum(sad, t[:, 0])
    return sad, gs, bs


def overheating(prices, cfg):
    opt = cfg["overheating"]
    k = opt["window"]
    rng = np.random.default_rng(1240)

    def simulate(n):
        return statistics(
            np.cumsum(rng.standard_normal((n, k)), axis=1), opt["minimum"]
        )

    _, null, _ = simulate(opt["null_draws"])
    raw = float(np.quantile(null, 0.95))
    adjusted = float(np.quantile(null, 1 - opt["family_alpha"] / len(opt["assets"])))
    _, independent, _ = simulate(1500)
    records = []
    summary = []
    for asset in opt["assets"]:
        p = (
            prices[(prices.symbol == asset) & (prices.day <= cfg["decision"])]
            .set_index("day")
            .close.dropna()
        )
        p.index = pd.to_datetime(p.index)
        p = p.resample("ME").last().dropna()
        logs = np.lib.stride_tricks.sliding_window_view(np.log(p), k)
        sad, gs, bs = statistics(logs, opt["minimum"])
        for j, when in enumerate(p.index[k - 1 :]):
            i = j + k - 1
            ahead = p.iloc[i + 1 : i + 7] / p.iloc[i] - 1
            hits = np.flatnonzero(ahead.to_numpy() <= -0.1)
            complete = len(ahead) == 6
            records.append(
                {
                    "asset": asset,
                    "month": when.strftime("%Y-%m"),
                    "sadf": sad[j],
                    "gsadf": gs[j],
                    "bsadf": bs[j],
                    "simple": bool(
                        p.iloc[i] / p.iloc[i - 6] - 1 > opt["simple_six_month_return"]
                    ),
                    "raw": bool(bs[j] > raw),
                    "adjusted": bool(bs[j] > adjusted),
                    "mature": complete,
                    "hit": bool(len(hits)) if complete else None,
                    "delay": int(hits[0] + 1) if len(hits) and complete else None,
                }
            )
    for rule in ["simple", "raw", "adjusted"]:
        for asset in opt["assets"]:
            rows = [
                z
                for z in records
                if z["asset"] == asset
                and z["mature"]
                and z["month"] >= cfg["final_start"][:7]
            ]
            alerts = [z for z in rows if z[rule]]
            summary.append(
                {
                    "asset": asset,
                    "rule": rule,
                    "evaluated": len(rows),
                    "alerts": len(alerts),
                    "false_alerts": sum(not z["hit"] for z in alerts),
                    "misses": sum(z["hit"] and not z[rule] for z in rows),
                    "delay_months": [z["delay"] for z in alerts if z["hit"]],
                }
            )
    return {
        "raw_critical": raw,
        "basket_critical": adjusted,
        "independent_null_exceedance": float(np.mean(independent > adjusted)),
        "null_checks": len(independent),
        "summary": summary,
        "records": records,
    }
