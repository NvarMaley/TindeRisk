"""Reproduce the section 4.1 tables and figures from the frozen prepared release."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from metrics import (
    ASSETS,
    LEVELS,
    WEIGHTS,
    attribution,
    block_estimates,
    coverage,
    forecasts,
    historical_tail,
    horizon_risk,
    underwater,
)

ROOT = Path(__file__).resolve().parents[2]
BASE = pd.Timestamp("2019-12-31")
END = pd.Timestamp("2026-10-30")
PORT = "Equal weight"
COLORS = ["#155B7B", "#B76031", "#9A7923", "#1A6755"]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def data():
    folder = ROOT / "data/prepared_v1"
    manifest = json.loads((folder / "manifest.json").read_text())
    for name in ("market.parquet", "usd_cash.parquet"):
        if digest(folder / name) != manifest[name]:
            raise ValueError(f"Input differs from prepared v1: {name}")
    m = pd.read_parquet(folder / "market.parquet")

    def wide(col):
        return (
            m.pivot(index="session", columns="asset", values=col).sort_index().loc[:END]
        )

    usd, chf = wide("usd_return"), wide("chf_return")
    fx = wide("chf_per_usd")
    if (
        not fx.eq(fx.SPY, axis=0)
        .where(fx.notna() | fx.SPY.notna().to_numpy()[:, None], True)
        .all()
        .all()
    ):
        raise ValueError("Inconsistent common currency fixings")
    usd[PORT] = usd[ASSETS].dot(WEIGHTS)
    chf[PORT] = chf[ASSETS].dot(WEIGHTS)
    cash = (
        pd.read_parquet(folder / "usd_cash.parquet").set_index("session").usd_cash_proxy
    )
    return usd, chf, fx.SPY, cash


def wealth_path(usd, fx):
    """Anchor wealth on base close; carry the USD investment through an unobserved FX mark."""
    if usd.iloc[1:].isna().any() or (usd.iloc[1:] < -1).any():
        raise ValueError("An uninterrupted valid USD return path is required")
    growth = 1 + usd.copy()
    growth.iloc[0] = 1.0
    wealth_usd = 100 * growth.cumprod(skipna=False)
    if pd.isna(fx.iloc[0]) or fx.iloc[0] <= 0:
        raise ValueError("Missing opening CHF valuation")
    return wealth_usd, wealth_usd * fx / fx.iloc[0]


def return_tables(usd, chf, fx, cash, out):
    dates = usd.loc[BASE:END].index
    if (dates[0], dates[-1]) != (BASE, END):
        raise ValueError("Missing measurement endpoint")
    samples, summary, episodes = [], [], []
    years = (END - BASE).days / 365.25
    for asset in usd:
        local = usd.loc[dates, asset].copy()
        base = chf.loc[dates, asset].copy()
        base.iloc[0] = local.iloc[0] = np.nan
        wu, wc = wealth_path(local, fx.loc[dates])
        excess = local - cash.reindex(dates)
        dd, age, events = underwater(wc)
        with np.errstate(divide="ignore"):
            day = pd.DataFrame(
                {
                    "asset": asset,
                    "usd_simple": local,
                    "usd_log": np.log1p(local),
                    "usd_excess": excess,
                    "chf_simple": base,
                    "chf_log": np.log1p(base),
                    "chf_excess": np.nan,
                    "wealth_usd": wu,
                    "wealth_chf": wc,
                    "drawdown_chf": dd,
                    "days_underwater": age,
                }
            )
        np.testing.assert_allclose(
            wc.pct_change(fill_method=None), base, atol=2e-12, equal_nan=True
        )
        samples.append(day.rename_axis("session").reset_index())
        episodes.append(events.assign(asset=asset))
        for currency, ret, wealth in [("USD", local, wu), ("CHF", base, wc)]:
            if pd.isna(wealth.iloc[-1]):
                raise ValueError("Ending mark unavailable")
            summary.append(
                {
                    "asset": asset,
                    "currency": currency,
                    "base": BASE,
                    "end": END,
                    "elapsed_years": years,
                    "sessions": len(dates) - 1,
                    "observed": ret.count(),
                    "missing_returns": len(dates) - 1 - ret.count(),
                    "total_losses": (ret == -1).sum(),
                    "missing_marks": wealth.isna().sum(),
                    "arithmetic_mean_daily": ret.mean(),
                    "arithmetic_annual_252": 252 * ret.mean(),
                    "mean_daily_excess": excess.mean() if currency == "USD" else np.nan,
                    "compounded_return": wealth.iloc[-1] / 100 - 1,
                    "cagr": (wealth.iloc[-1] / 100) ** (1 / years) - 1,
                    "iid_annual_vol": ret.std() * np.sqrt(252),
                }
            )
    daily = pd.concat(samples, ignore_index=True)
    daily.to_parquet(out / "daily.parquet", index=False)
    pd.DataFrame(summary).to_csv(out / "returns.csv", index=False)
    events = pd.concat(episodes, ignore_index=True)
    events.to_csv(out / "drawdown_episodes.csv", index=False)
    return daily


def tail_tables(chf, out):
    dates = chf.loc[BASE:END].index[1:]
    tails, checks, ledgers, horizons = [], [], [], []
    for asset in [*ASSETS, PORT]:
        observed = chf.loc[dates, asset]
        x = -observed.to_numpy()
        horizons.append(dict(asset=asset, **horizon_risk(observed)))

        def statistic(y):
            return np.array([val for p in LEVELS for val in historical_tail(y, p)])

        for length in [5, 20] if asset == PORT else [5]:
            lower, upper = block_estimates(x, statistic, length)
            for i, p in enumerate(LEVELS):
                v, e = historical_tail(x, p)
                n = observed.count()
                hit = x > v
                tails.append(
                    {
                        "asset": asset,
                        "level": p,
                        "observed": n,
                        "block_sessions": length,
                        "var": v,
                        "es": e,
                        "tail_mass": n * (1 - p),
                        "sparse_tail": n * (1 - p) < 20,
                        "strict_tail": hit.sum(),
                        "ties": (x == v).sum(),
                        "tail_runs": (hit & ~np.r_[False, hit[:-1]]).sum(),
                        "var_low": lower[2 * i],
                        "var_high": upper[2 * i],
                        "es_low": lower[2 * i + 1],
                        "es_high": upper[2 * i + 1],
                    }
                )
        for p in LEVELS:
            ledger = forecasts(chf[asset], dates, p).assign(asset=asset)
            ledgers.append(ledger)
            checks.append(dict(asset=asset, **coverage(ledger, p)))
    pd.DataFrame(tails).to_csv(out / "historical_tails.csv", index=False)
    pd.DataFrame(checks).to_csv(out / "var_backtest.csv", index=False)
    pd.concat(ledgers, ignore_index=True).to_parquet(
        out / "forecast_ledger.parquet", index=False
    )
    pd.DataFrame(horizons).to_csv(out / "horizon_risk.csv", index=False)


def attribution_tables(chf, out):
    sample = chf.loc[(chf.index > BASE) & (chf.index <= END), ASSETS]
    rows, matrices = [], []
    for window in [63, 252, 756, len(sample)]:
        x = sample.tail(window)
        common = x.dropna()
        cov = common.cov().to_numpy() * 252
        diagnostics, parts = attribution(cov, WEIGHTS)
        if parts is None:
            raise ValueError(f"Portfolio attribution undefined: {diagnostics}")

        def risk_share(block):
            c = np.cov(block[np.isfinite(block).all(axis=1)].T, ddof=1)
            variance = WEIGHTS @ c @ WEIGHTS
            return (
                WEIGHTS * (c @ WEIGHTS) / variance
                if variance > 1e-16
                else np.full(3, np.nan)
            )

        lower, upper = block_estimates(x.to_numpy(), risk_share, 5)
        for i, asset in enumerate(ASSETS):
            rows.append(
                dict(
                    window=window,
                    first=x.index[0],
                    last=x.index[-1],
                    observed=len(common),
                    asset=asset,
                    weight=WEIGHTS[i],
                    **{k: v[i] for k, v in parts.items()},
                    share_low=lower[i],
                    share_high=upper[i],
                    **{k: v for k, v in diagnostics.items() if k != "eigenvalues"},
                    eig_min=diagnostics["eigenvalues"][0],
                    eig_mid=diagnostics["eigenvalues"][1],
                    eig_max=diagnostics["eigenvalues"][2],
                )
            )
        corr = common.corr().to_numpy()
        for i, left in enumerate(ASSETS):
            for j, right in enumerate(ASSETS):
                matrices.append(
                    {
                        "window": window,
                        "left": left,
                        "right": right,
                        "cov_annual": cov[i, j],
                        "correlation": corr[i, j],
                    }
                )
    pd.DataFrame(rows).to_csv(out / "risk_contributions.csv", index=False)
    pd.DataFrame(matrices).to_csv(out / "dependence.csv", index=False)
    all_returns = chf[ASSETS]
    rolling = pd.DataFrame(
        {
            f"{a}/{b}": all_returns[a].rolling(63, min_periods=60).corr(all_returns[b])
            for i, a in enumerate(ASSETS)
            for b in ASSETS[i + 1 :]
        },
        index=all_returns.index,
    ).loc[sample.index]
    rolling.to_parquet(out / "rolling_correlations.parquet")
    return rolling


def figures(daily, rolling, out):
    d = daily[daily.asset.eq(PORT)].set_index("session")
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(10, 8.8),
        sharex=True,
        height_ratios=[3, 1.5, 1.5, 1.05],
        layout="constrained",
    )
    fig.suptitle("Historical wealth and losses in Swiss francs", fontsize=16)
    for asset, color in zip([*ASSETS, PORT], COLORS):
        one = daily[daily.asset.eq(asset)]
        axes[0].plot(
            one.session,
            one.wealth_chf,
            label=asset,
            color=color,
            lw=2 if asset == PORT else 1,
        )
    axes[0].set_ylabel("Wealth (base 100)")
    axes[0].legend(ncol=4, loc="upper left", fontsize=9)
    axes[1].fill_between(d.index, 100 * d.drawdown_chf, 0, color=COLORS[3])
    axes[1].set_ylabel("Portfolio\ndrawdown (%)")
    axes[2].plot(d.index, d.days_underwater, color="#574981", lw=1.2)
    axes[2].set_ylabel("Days below\nobserved peak")
    avail = (
        daily[daily.asset.isin(ASSETS)]
        .pivot(index="session", columns="asset", values="chf_simple")
        .iloc[1:]
        .notna()
        .sum(axis=1)
    )
    axes[3].step(avail.index, avail, where="mid", lw=0.8, color=COLORS[0])
    axes[3].set(
        yticks=[0, 3], ylim=(-0.3, 3.3), ylabel="Funds with a\ndaily CHF return"
    )
    for ax in axes:
        ax.grid(alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.savefig(out / "wealth_drawdown.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(
        1, 2, figsize=(11, 4), width_ratios=[1, 2.3], layout="constrained"
    )
    corr = (
        daily[daily.asset.isin(ASSETS)]
        .pivot(index="session", columns="asset", values="chf_simple")[ASSETS]
        .dropna()
        .corr()
    )
    axes[0].imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    axes[0].set(
        xticks=range(3),
        xticklabels=ASSETS,
        yticks=range(3),
        yticklabels=ASSETS,
        title="Full-period correlation",
    )
    for i in range(3):
        for j in range(3):
            val = corr.iloc[i, j]
            axes[0].text(
                j,
                i,
                f"{val:.2f}",
                ha="center",
                va="center",
                color="white" if abs(val) > 0.65 else "black",
            )
    for name, color in zip(rolling, COLORS):
        axes[1].plot(rolling.index, rolling[name], label=name, lw=1, color=color)
    axes[1].set(title="Rolling 63-session CHF correlations", ylim=(-1, 1))
    axes[1].axhline(0, lw=0.6, color="#374151")
    axes[1].legend(ncol=3, fontsize=8, loc="lower left")
    axes[1].grid(alpha=0.2)
    fig.savefig(out / "correlations.png", dpi=150)
    plt.close(fig)


def build(output):
    usd, chf, fx, cash = data()
    daily = return_tables(usd, chf, fx, cash, output)
    tail_tables(chf, output)
    rolling = attribution_tables(chf, output)
    figures(daily, rolling, output)
    hashes = {p.name: digest(p) for p in sorted(output.iterdir())}
    (output / "manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parent / "results"
    )
    out = parser.parse_args().output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as tmp:
        release = Path(tmp) / "results"
        release.mkdir()
        build(release)
        if out.exists():
            if {p.name: digest(p) for p in release.iterdir()} != {
                p.name: digest(p) for p in out.iterdir()
            }:
                raise ValueError(
                    "Existing output differs. Use --output to build a separate release."
                )
        else:
            release.rename(out)
    print(f"Verified historical metrics in {out}")
