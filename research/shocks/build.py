"""Build section 4.2 evidence from the frozen inputs. Run from any directory."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.shocks.analysis import (
    ASSETS,
    EPISODES,
    FACTORS,
    MIXES,
    TERMS,
    episode_return,
    fit,
    matched,
    scenarios,
    training_window,
)

ROOT = Path(__file__).resolve().parents[2]
END = "2026-10-30"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def load_panel(assets=ASSETS):
    market_path = ROOT / "data/prepared_v1/market.parquet"
    manifest = json.loads((market_path.parent / "manifest.json").read_text())
    if digest(market_path) != manifest[market_path.name]:
        raise ValueError("Prepared market input differs")
    market = pd.read_parquet(market_path)
    frame = (
        market.pivot(index="session", columns="asset", values="usd_return")[
            list(assets)
        ]
        .loc[:END]
        .copy()
    )
    spot = market[market.asset == "SPY"].set_index("session").reindex(frame.index)
    frame["fx"] = spot.fx_return
    frame["fixing"] = spot.chf_per_usd
    frame["equity"] = frame.SPY
    raw = pd.read_csv(ROOT / "research/source_catalogue/raw_manifest_v1.csv").set_index(
        "path"
    )
    for name, path in {
        "nominal": "data/raw/public_phase2/DGS10.csv",
        "breakeven": "data/raw/public_phase2/T10YIE.csv",
        "vix": "data/raw/VIXCLS.csv",
    }.items():
        if digest(ROOT / path) != raw.at[path, "sha256"]:
            raise ValueError(f"Raw input differs: {path}")
        series = (
            pd.read_csv(
                ROOT / path,
                index_col="observation_date",
                parse_dates=True,
                na_values=["."],
            )
            .iloc[:, 0]
            .reindex(frame.index)
        )
        frame[name] = series.shift(1) if name == "vix" else series.diff() / 100
    frame["regime"] = np.select(
        [frame.vix.isna(), frame.vix <= 20, frame.vix >= 30],
        ["unknown", "calm", "stress"],
        default="intermediate",
    )
    frame["episode"] = "outside"
    for label, (start, end) in EPISODES.items():
        frame.loc[start:end, "episode"] = label
    return frame


def exposure_rows(beta, se, n, **info):
    return [
        dict(
            **info,
            asset=asset,
            term=name,
            n=n,
            beta=beta[k, i],
            low=beta[k, i] - 1.96 * se[k, i],
            high=beta[k, i] + 1.96 * se[k, i],
        )
        for i, asset in enumerate(ASSETS)
        for k, name in enumerate(TERMS)
    ]


def plot_sensitivities(exposures, out):
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True, layout="constrained")
    for ax, asset, term, size, title, color in zip(
        axes,
        ("IEF", "GLD"),
        ("nominal", "breakeven"),
        (0.01, 0.005),
        (
            "Treasury fund (IEF), nominal yield +100 bp",
            "Gold (GLD), breakeven inflation +50 bp",
        ),
        ("#19627b", "#965d22"),
    ):
        subset = exposures[exposures.asset.eq(asset) & exposures.term.eq(term)]
        ax.fill_between(
            subset.cutoff,
            100 * size * subset.low,
            100 * size * subset.high,
            alpha=0.19,
            color=color,
            label="95% coefficient interval",
        )
        ax.plot(
            subset.cutoff,
            100 * size * subset.beta,
            color=color,
            label="Estimated response",
        )
        ax.axhline(0, color="#4c5052", linewidth=0.7)
        ax.set_title(title, loc="left")
        ax.set_ylabel("USD return (%)")
        ax.grid(axis="y", alpha=0.18)
    axes[0].legend(loc="best", ncol=2, fontsize=8)
    axes[-1].set_xlabel("Estimation month-end")
    fig.savefig(out / "rolling_sensitivities.png", dpi=150)
    plt.close(fig)


def build(out):
    panel = load_panel()
    hist = panel.loc["2020":END]
    month_ends = (
        panel.loc["2019-12":END]
        .groupby(panel.loc["2019-12":END].index.to_period("M"))
        .tail(1)
        .index
    )
    exposures, holdings, totals, ledgers = [], [], [], []
    for cutoff in month_ends:
        train = training_window(panel, cutoff)
        beta, se, n = fit(train, 200)
        exposures.extend(
            exposure_rows(
                beta,
                se,
                n,
                cutoff=cutoff,
                first=train.index[0],
                last=train.index[-1],
                scheduled=len(train),
            )
        )
        detail, summary = scenarios(beta)
        holdings.extend(dict(cutoff=cutoff, **r) for r in detail)
        totals.extend(dict(cutoff=cutoff, **r) for r in summary)
        month = hist.loc[hist.index.to_period("M") == cutoff.to_period("M") + 1]
        if month.empty:
            continue
        factors = month[FACTORS].to_numpy()
        explained_usd = beta[0] + factors @ beta[1:]
        for mix, w in MIXES.items():
            ledger = month[["regime", "episode"]].copy()
            ledger["cutoff"] = cutoff
            ledger["mix"] = mix
            ledger["actual"] = (1 + month[ASSETS] @ w) * (1 + month.fx) - 1
            ledger["explained"] = (1 + explained_usd @ w) * (1 + month.fx) - 1
            ledger["residual"] = ledger.actual - ledger.explained
            ledgers.append(ledger.reset_index())
    ledger = pd.concat(ledgers, ignore_index=True)
    ledger.to_parquet(out / "historical_attribution.parquet", index=False)
    exposure_table = pd.DataFrame(exposures)
    exposure_table.to_csv(out / "rolling_exposures.csv", index=False)
    plot_sensitivities(exposure_table, out)
    pd.DataFrame(holdings).to_csv(out / "scenario_holdings.csv", index=False)
    pd.DataFrame(totals).to_csv(out / "scenarios.csv", index=False)
    summaries = []
    fits = []

    def summarize(label, mask, kind, period=None):
        sub = hist.where(mask, axis=0)
        n = matched(sub).sum()
        # Keeping empty grid rows prevents HAC from linking disjoint episodes.
        if n >= 20:
            b, s, count = fit(sub, 20)
            fits.extend(exposure_rows(b, s, count, kind=kind, sample=label))
        for mix, w in MIXES.items():
            part = ledger[ledger.mix.eq(mix) & ledger.session.isin(hist.index[mask])]
            pairs = part.dropna(subset=["actual", "explained"])
            if len(pairs) != n:
                raise ValueError("Mismatch between attribution and exposure samples")
            summaries.append(
                {
                    "kind": kind,
                    "sample": label,
                    "mix": mix,
                    "scheduled": len(part),
                    "observed_chf": part.actual.count(),
                    "matched": n,
                    "mean_daily": pairs.actual.mean(),
                    "daily_sd": pairs.actual.std(),
                    "mean_explained": pairs.explained.mean(),
                    "residual_rmse": np.sqrt((pairs.residual**2).mean()),
                    "compounded_chf": episode_return(panel, *period, w)
                    if period
                    else np.nan,
                }
            )

    for regime in ("calm", "intermediate", "stress", "unknown"):
        summarize(regime, hist.regime.eq(regime), "prior VIX")
    endpoints = []
    for label, period in EPISODES.items():
        # Show exactly which close-to-close interval each available total covers.
        target = panel.loc[slice(*period)]
        anchor = panel.index[panel.index.get_loc(target.index[0]) - 1]
        eligible = panel.loc[anchor : target.index[-1], "fixing"].dropna()
        actual_start, actual_end = eligible.index[[0, -1]]
        first_return = panel.index[panel.index.get_loc(actual_start) + 1]
        for mix, w in MIXES.items():
            endpoints.append(
                {
                    "episode": label,
                    "mix": mix,
                    "requested_base": anchor,
                    "requested_end": target.index[-1],
                    "measured_base": actual_start,
                    "measured_end": actual_end,
                    "exact": (
                        actual_start == anchor and actual_end == target.index[-1]
                    ),
                    "compounded_chf": episode_return(
                        panel, first_return, actual_end, w
                    ),
                }
            )
        summarize(label, hist.episode.eq(label), "episode", period)
    pd.DataFrame(endpoints).to_csv(out / "episode_endpoints.csv", index=False)
    crisis = hist.episode.ne("outside")
    summarize("all episodes", crisis, "episode sensitivity")
    for label in EPISODES:
        summarize(
            f"omit {label}", crisis & hist.episode.ne(label), "episode sensitivity"
        )
    pd.DataFrame(summaries).to_csv(out / "historical_summary.csv", index=False)
    pd.DataFrame(fits).to_csv(out / "subsample_exposures.csv", index=False)
    hashes = {p.name: digest(p) for p in sorted(out.iterdir())}
    (out / "manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("results")
    )
    output = parser.parse_args().output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "release"
        stage.mkdir()
        build(stage)
        if output.exists():
            if {p.name: digest(p) for p in stage.iterdir()} != {
                p.name: digest(p) for p in output.iterdir()
            }:
                raise ValueError(
                    "Existing release differs. Use --output for a separate build."
                )
        else:
            stage.rename(output)
    print(f"Verified section 4.2 results in {output}")
