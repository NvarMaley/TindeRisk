"""Dated paired scores and temporal diagnostics. All inference is retrospective."""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from models import BASE, CAND
from scipy.stats import norm
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import adfuller, kpss, pacf


def blocks(values, length, seed=501, draws=1999):
    x = np.asarray(values, dtype=float)
    n = len(x)
    if np.isfinite(x).sum() < 2 * length or n < length:
        return np.full(3, np.nan)
    starts = np.random.default_rng(seed).integers(
        0, n - length + 1, (draws, (n + length - 1) // length)
    )
    draw = x[(starts[:, :, None] + np.arange(length)).reshape(draws, -1)[:, :n]]
    counts = np.isfinite(draw).sum(axis=1)
    means = np.nansum(draw, axis=1)[counts > 0] / counts[counts > 0]
    return np.quantile(means, [0.025, 0.975, 0.05 / 7])


def paired(forecasts, alloc, sent, register, frozen, out):
    rows = []
    detail = []
    selection = []
    for study in BASE:
        if study in ["H01", "H02", "H03", "H04"]:
            score = forecasts[forecasts.study == study].copy()
            scale = (
                score.loc[
                    (score.phase == "development") & (score.arm == BASE[study]), "loss"
                ].mean()
                if study in ["H03", "H04"]
                else 1.0
            )
            score["value"] = -score.loss / scale
            score["deployed"] = -score.deployed_loss / scale
        elif study in ["H06", "H07"]:
            score = sent if study == "H06" else alloc
            score = score[(score.study == study) & score.cost_bp.eq(10)].copy()
            score["value"] = score.utility if study == "H06" else score.net_return
            score["deployed"] = score.value
        else:
            score = frozen[frozen.study == study].copy()
            score["value"] = score["deployed"] = np.nan
        for phase, g in score[score.phase != "warm-up"].groupby("phase", sort=False):
            wide = g.pivot(index="holding_month", columns="arm", values="value")
            dep = g.pivot(index="holding_month", columns="arm", values="deployed")
            for arm in wide:
                if arm == BASE[study]:
                    continue
                diff = wide[arm] - wide[BASE[study]]
                deployed = dep[arm] - dep[BASE[study]]
                for mo, delta in diff.items():
                    detail.append(
                        {
                            "study": study,
                            "phase": phase,
                            "arm": arm,
                            "holding_month": mo,
                            "gain": delta,
                            "deployed_gain": deployed.at[mo],
                        }
                    )
                for length in [1, 3, 6]:
                    lo, hi, sim = blocks(diff, length)
                    rows.append(
                        {
                            "study": study,
                            "phase": phase,
                            "arm": arm,
                            "block": length,
                            "scheduled": len(diff),
                            "paired": diff.count(),
                            "gain": diff.mean(),
                            "low": lo,
                            "high": hi,
                            "seven_way_lower": sim,
                            "deployed_n": deployed.count(),
                            "deployed_gain": deployed.mean(),
                            "late_start_gain": diff.iloc[12:].mean(),
                        }
                    )
        candidates = [
            r
            for r in rows
            if r["study"] == study
            and r["phase"] == "validation"
            and r["block"] == 3
            and r["arm"] in CAND[study]
            and np.isfinite(r["gain"])
        ]
        selected = (
            max(candidates, key=lambda r: (r["gain"], -CAND[study].index(r["arm"])))[
                "arm"
            ]
            if candidates
            else None
        )
        replay = next(
            (
                r
                for r in rows
                if r["study"] == study
                and r["phase"] == "historical replay"
                and r["arm"] == selected
                and r["block"] == 3
            ),
            {},
        )
        selection.append(
            {
                "study": study,
                "validation_choice": selected,
                "minimum_gain": register.at[study, "minimum_gain"],
                "historical_gain": replay.get("gain"),
                "historical_pairs": replay.get("paired", 0),
                "independent_pairs": 0,
                "decision": "retain reference"
                if study != "H05"
                else "withhold stock sleeve",
            }
        )
    pd.DataFrame(rows).to_csv(out / "paired_comparisons.csv", index=False)
    pd.DataFrame(detail).to_parquet(out / "paired_months.parquet", index=False)
    pd.DataFrame(selection).to_csv(out / "decisions.csv", index=False)


def calibration(forecasts, f, out):
    summary = []
    diagnostics = []
    for (study, arm), g in forecasts[
        (forecasts.phase == "historical replay") & forecasts.study.isin(["H03", "H04"])
    ].groupby(["study", "arm"]):
        g = g.sort_values("origin").copy()
        # Prior month-end VIX is a descriptive state observed before the holding month.
        g["state"] = g.origin.map(f["prior_vix"]).map(
            lambda v: (
                "unknown"
                if pd.isna(v)
                else "calm"
                if v <= 20
                else "stress"
                if v >= 30
                else "intermediate"
            )
        )
        for name, mask in [
            ("all", np.ones(len(g), bool)),
            *[
                (s, g.state.eq(s))
                for s in ["calm", "intermediate", "stress", "unknown"]
            ],
            ("2020–22", g.holding_month < "2023"),
            ("2023 onward", g.holding_month >= "2023"),
        ]:
            v = g[mask].dropna(subset=["lower", "upper", "actual"])
            n = len(v)
            low = v.actual < v.lower
            high = v.actual > v.upper
            covered = (~(low | high)).astype(float)
            full = covered.reindex(g.index)
            ci = blocks(full, 3)
            miss = (full == 0).to_numpy()

            def pin(q, col, v=v):
                err = v.actual - v[col]
                return np.maximum(q * err, (q - 1) * err).mean()

            summary.append(
                {
                    "study": study,
                    "arm": arm,
                    "group": name,
                    "n": n,
                    "coverage": covered.mean(),
                    "low": ci[0],
                    "high": ci[1],
                    "width": (v.upper - v.lower).mean(),
                    "misses_below": low.sum(),
                    "misses_above": high.sum(),
                    "adjacent_misses": (miss[1:] & miss[:-1]).sum(),
                    "pinball10": pin(0.1, "lower"),
                    "pinball90": pin(0.9, "upper"),
                }
            )
        e = (g.actual - g.point).dropna()
        top = e.abs().idxmax()
        lm = het_arch(e, nlags=3)
        diagnostics.append(
            {
                "study": study,
                "arm": arm,
                "n": len(e),
                "mean": e.mean(),
                "rmse": np.sqrt((e**2).mean()),
                "acf1": e.autocorr(),
                "pacf1": pacf(e, nlags=1)[1],
                "ljung_box_p": acorr_ljungbox(e, lags=[3]).lb_pvalue.iloc[0],
                "arch_lm_p": lm[1],
                "largest_error_month": g.loc[top, "holding_month"],
                "largest_error": e[top],
            }
        )
    pd.DataFrame(summary).to_csv(out / "interval_calibration.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(out / "residual_checks.csv", index=False)


def series_tests(tables, out):
    rows = []
    for name, tab in tables.items():
        dev = tab.loc["2010":"2015-12"]
        for series in (
            ["target", "T10Y2Y", "CPIAUCSL", "UNRATE", "INDPRO"]
            if name == "H03"
            else ["target", "BAA10Y"]
        ):
            for form in ["level", "difference"]:
                x = dev[series] if form == "level" else dev[series].diff()
                x = x.dropna()
                for deterministic in ["c", "ct"]:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        k = kpss(x, regression=deterministic, nlags="auto")
                        a = adfuller(
                            x, regression=deterministic, maxlag=6, autolag="AIC"
                        )
                    rows.append(
                        {
                            "study": name,
                            "variable": series,
                            "form": form,
                            "deterministic": deterministic,
                            "n": len(x),
                            "adf_p": a[1],
                            "adf_lags": a[2],
                            "kpss_p_capped": k[1],
                            "kpss_lags": k[2],
                            "acf1": x.autocorr(),
                            "first_half_mean": x.iloc[: len(x) // 2].mean(),
                            "second_half_mean": x.iloc[len(x) // 2 :].mean(),
                        }
                    )
    pd.DataFrame(rows).to_csv(out / "development_diagnostics.csv", index=False)


def walk_predictions(x, y):
    # Fixed expanding standardization/ridge, equivalent to sklearn with an unpenalized intercept.
    count = len(y)
    result = np.full((count, 3), np.nan)
    sx = np.cumsum(x, axis=0)
    sy = np.cumsum(y)
    xy = np.cumsum(x * y[:, None], axis=0)
    xx = np.cumsum(x[:, :, None] * x[:, None, :], axis=0)
    for t in range(37, count):
        n = t - 1
        j = n - 1
        mx = sx[j] / n
        my = sy[j] / n
        gram = xx[j] - n * np.outer(mx, mx)
        rhs = xy[j] - n * mx * my
        result[t] = [
            my,
            my + (x[t] - mx) @ np.linalg.solve(gram, rhs),
            my + (x[t] - mx) @ np.linalg.solve(gram + np.diag(np.diag(gram) / n), rhs),
        ]
    return result


def equity_null(table, out):
    t = table.dropna(subset=["T10Y2Y", "BAA10Y", "target"])
    x = t[["T10Y2Y", "BAA10Y"]].to_numpy()
    y = t.target.to_numpy()
    dev = t.index < "2016"
    val = (t.index >= "2016") & (t.index < "2020")
    test = t.index >= "2020"
    # Innovations in x[t+1] may correlate with y[t], preserving predictive-regression endogeneity.
    z = np.column_stack((np.ones(len(x) - 1), x[:-1]))
    mask = dev[1:]
    co = np.linalg.lstsq(z[mask], x[1:][mask], rcond=None)[0]
    if np.max(abs(np.linalg.eigvals(co[1:]))) >= 1:
        raise ValueError("Unstable simulated spread dynamics")
    innovations = np.c_[x[1:] - z @ co, y[:-1] - y[dev].mean()][mask]
    innovations -= innovations.mean(0)
    rng = np.random.default_rng(504)
    results = []
    for i in range(200):
        xx = x
        yy = y
        if i:
            starts = rng.integers(0, len(innovations) - 2, (len(x) + 2) // 3)
            eps = innovations[(starts[:, None] + np.arange(3)).ravel()[: len(x)]]
            xx = np.empty_like(x)
            xx[0] = x[0]
            for j in range(len(x) - 1):
                xx[j + 1] = co[0] + xx[j] @ co[1:] + eps[j, :2]
            yy = y[dev].mean() + eps[:, 2]
        pred = walk_predictions(xx, yy)
        loss = (yy[:, None] - pred) ** 2
        best = 1 + np.nanargmin(np.nanmean(loss[val, 1:], axis=0))
        r2 = 1 - loss[test, best].sum() / loss[test, 0].sum()
        results.append(
            {"draw": i, "selected": ["mean", "OLS", "ridge"][best], "historical_r2": r2}
        )
    pd.DataFrame(results).to_csv(out / "predictability_null.csv", index=False)


def forecast_comparison(f, out):
    rows = []
    for study, part in f[(f.phase == "historical replay")].groupby("study"):
        base = part[part.arm == BASE[study]].set_index("holding_month")
        for arm, g in part.groupby("arm"):
            if arm == BASE[study]:
                continue
            a = g.set_index("holding_month")
            p = pd.concat([base.point, a.point, a.actual, base.loss, a.loss], axis=1)
            p.columns = ["b", "c", "y", "bl", "cl"]
            p = p.dropna()
            if len(p) < 6:
                continue
            diff = p.bl - p.cl
            kind = "paired blocks only"
            pv = np.nan
            if study in ["H03", "H04"] and (arm == "slope + macro PC" or arm == "OLS"):
                adjusted = diff + (p.b - p.c) ** 2
                fit = sm.OLS(adjusted, np.ones(len(p))).fit(
                    cov_type="HAC", cov_kwds={"maxlags": 3}
                )
                kind = "Clark-West approximate one-sided"
                pv = norm.sf(fit.tvalues.iloc[0])
            elif study == "H02" and arm == "EWMA":
                # Gap-aware HAC on scheduled origins. Missing scores contribute zero centered score.
                grid = (base.loss - a.loss).reindex(base.index)
                u = (grid - grid.mean()).fillna(0).to_numpy()
                long = (u @ u) + 2 * sum(
                    (1 - k / 4) * (u[k:] @ u[:-k]) for k in range(1, 4)
                )
                if long > 0:
                    pv = 2 * norm.sf(abs(diff.mean() * len(diff) / np.sqrt(long)))
                    kind = "DM asymptotic two-sided HAC3"
            rows.append(
                {
                    "study": study,
                    "arm": arm,
                    "n": len(p),
                    "baseline_loss": p.bl.mean(),
                    "candidate_loss": p.cl.mean(),
                    "r2_os": 1 - p.cl.sum() / p.bl.sum()
                    if study in ["H03", "H04"]
                    else np.nan,
                    "error_corr": (p.y - p.b).corr(p.y - p.c),
                    "test": kind,
                    "diagnostic_p": pv,
                }
            )
    pd.DataFrame(rows).to_csv(out / "forecast_comparisons.csv", index=False)


def selection_sensitivity(out):
    """Joint centered gain bootstrap across registered rivals on identical monthly blocks."""
    gains = pd.read_parquet(out / "paired_months.parquet")
    rows = []
    for study, g in gains[gains.phase == "historical replay"].groupby("study"):
        wide = (
            g[g.arm.isin(CAND[study])]
            .pivot(index="holding_month", columns="arm", values="gain")
            .dropna(how="all", axis=1)
        )
        n, k = wide.shape
        if k < 2:
            continue
        same = wide.notna().all(axis=1)
        x = wide.where(same, axis=0).to_numpy()
        obs = np.nanmean(x, axis=0)
        center = x - obs
        starts = np.random.default_rng(501).integers(
            0, n - 2, size=(1999, (n + 2) // 3)
        )
        index = (starts[:, :, None] + np.arange(3)).reshape(1999, -1)[:, :n]
        null = np.nanmax(np.nanmean(center[index], axis=1), axis=1)
        rows.append(
            {
                "study": study,
                "arms": " | ".join(wide.columns),
                "common": same.sum(),
                "max_gain": obs.max(),
                "joint_p": (1 + (null >= obs.max()).sum()) / (len(null) + 1),
            }
        )
    pd.DataFrame(rows).to_csv(out / "selection_sensitivity.csv", index=False)


def economic_effects(alloc, sent, out):
    together = pd.concat([alloc, sent], ignore_index=True)
    rows = []
    for (study, phase, bp), g in together.groupby(["study", "phase", "cost_bp"]):
        ref = g[g.arm == BASE[study]].set_index("holding_month")
        for arm, part in g.groupby("arm"):
            if arm == BASE[study]:
                continue
            cand = part.set_index("holding_month")
            diff = cand.utility - ref.utility
            lo, hi, _ = blocks(diff, 3)
            rows.append(
                {
                    "study": study,
                    "phase": phase,
                    "arm": arm,
                    "cost_bp": bp,
                    "paired": diff.count(),
                    "gain_net_utility": diff.mean(),
                    "low": lo,
                    "high": hi,
                    "mean_net_return_difference": (
                        cand.net_return - ref.net_return
                    ).mean(),
                    "terminal_difference": cand.wealth.iloc[-1] - ref.wealth.iloc[-1]
                    if study != "H06"
                    else np.nan,
                }
            )
    pd.DataFrame(rows).to_csv(out / "economic_effects.csv", index=False)


def residual_plot(f, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(9, 5), layout="constrained")
    for ax, (study, title, color) in zip(
        axes,
        [
            ("H03", "Treasury fund (IEF)", "#19627b"),
            ("H04", "US equities (SPY)", "#86592a"),
        ],
    ):
        p = f[
            (f.phase == "historical replay")
            & (f.study == study)
            & (f.arm == BASE[study])
        ]
        ax.plot(
            p.end,
            100 * (p.actual - p.point),
            color=color,
            lw=1.1,
            label="Realized minus forecast",
        )
        ax.fill_between(
            p.end,
            100 * (p.lower - p.point),
            100 * (p.upper - p.point),
            color=color,
            alpha=0.16,
            label="Nominal 80% error range",
        )
        ax.axhline(0, lw=0.7, color="black")
        ax.set_title(title, loc="left")
        ax.set_ylabel("USD return (pp)")
        ax.grid(alpha=0.18)
    axes[0].legend(fontsize=8, ncol=2)
    axes[-1].set_xlabel("Holding month end")
    fig.savefig(out / "monthly_errors.png", dpi=135)
    plt.close(fig)
