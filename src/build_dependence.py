"""Reproduce checklist 2.1b and 2.2: python -m src.build_dependence."""

import json
from datetime import UTC, datetime
from importlib.metadata import version

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .correlation import correlation_diagnostics
from .estimation import rolling_covariances
from .paths import ROOT, PROCESSED_DATA, RESULTS
from .provenance import sha256_file


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    sample_path = PROCESSED_DATA / "common_sample_manifest.json"
    sample = json.loads(sample_path.read_text())
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    benchmark = config["benchmark"]
    window = 252 * config["portfolio"]["estimation_window_years"]
    manifest = {"created_utc": datetime.now(UTC).isoformat(),
        "scope": "2.1b asset correlations and 2.2 covariance diagnostics; no strategy ranking or forecast",
        "sample_manifest_sha256": sha256_file(sample_path),
        "config_sha256": sha256_file(config_path),
        "runtime_versions": {name: version(name) for name in
            ["numpy", "pandas", "scikit-learn", "matplotlib", "pandas-market-calendars"]},
        "rolling_correlation_window": 252, "covariance_window": window,
        "covariance_ddof": 1, "annualization": 252,
        "decision_timing": "last NYSE session of completed month, after close; includes that close, usable afterward",
        "correlation_initial_rows": "first 251 observations undefined; no cross-period warm-up",
        "covariance_universe": assets, "files": {}, "periods": {}}
    RESULTS.mkdir(exist_ok=True, parents=True)
    for period in config["validation"]["periods"]:
        inputs = {}
        for key in ["returns", "warmup_returns"]:
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != sample["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            inputs[key] = pd.read_parquet(path)
        returns = inputs["returns"]
        if list(returns.columns) != assets + [benchmark]:
            raise ValueError("return universe differs from config")
        history = pd.concat([inputs["warmup_returns"], returns])[assets]
        if history.index.has_duplicates or not history.index.is_monotonic_increasing:
            raise ValueError("warm-up and sample must be disjoint and ordered")
        corr, rolling = correlation_diagnostics(returns, benchmark=benchmark,
            diversifiers=config["tickers"]["diversifiers"])
        start, end = returns.index.min(), returns.index.max()
        # Use exchange month-ends, never the last available row of a partial month.
        schedule = mcal.get_calendar("NYSE").valid_days(
            start.replace(day=1), end + pd.offsets.MonthEnd(0), tz=None)
        month_ends = pd.Series(schedule, index=schedule).groupby(schedule.to_period("M")).last()
        dates = pd.DatetimeIndex(month_ends[month_ends.isin(returns.index)])
        covariances, diagnostics = rolling_covariances(history, dates, window=window)
        prefix = f"2_1b_{period}"
        tables = {f"{prefix}_correlation.csv": corr,
                  f"{prefix}_rolling_correlation.csv": rolling,
                  f"2_2_{period}_diagnostics.csv": diagnostics}
        for name, table in tables.items():
            table.to_csv(RESULTS / name)
        cov_path = RESULTS / f"2_2_{period}_covariances.parquet"
        covariances.to_parquet(cov_path)
        generated = list(tables) + [cov_path.name]
        fig, ax = plt.subplots(figsize=(11, 9), layout="constrained")
        plot = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr)), corr.index)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(corr.iloc[i,j]) > .65 else "black")
        fig.colorbar(plot, ax=ax, label="Pearson correlation")
        ax.set_title(f"Daily return correlations — {period}\n{start.date()} to {end.date()} · descriptive")
        name = f"{prefix}_heatmap.png"
        fig.savefig(RESULTS / name, dpi=160); plt.close(fig); generated.append(name)
        fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
        rolling.plot(ax=ax, linewidth=1)
        ax.axhline(0, color="gray", linestyle="--", linewidth=.8)
        ax.set_ylim(-1, 1); ax.set_ylabel("Pearson correlation")
        ax.set_title(f"Trailing 252-session correlation with {benchmark} — {period}")
        ax.set_xlabel("Session · first 251 values undefined · historical, not predictive")
        name = f"{prefix}_rolling.png"
        fig.savefig(RESULTS / name, dpi=160); plt.close(fig); generated.append(name)
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout="constrained", sharex=True)
        diagnostics.condition_number.unstack().plot(ax=axes[0], logy=True)
        axes[0].set_ylabel("Condition number (log scale)")
        diagnostics.shrinkage.unstack()[["lw_constcorr", "lw_identity"]].plot(ax=axes[1])
        axes[1].set_ylim(0, min(1, max(.1, diagnostics.shrinkage.max() * 1.15)))
        axes[1].set_ylabel("Shrinkage intensity")
        axes[1].set_xlabel(f"Month-end close · {window} trailing sessions · {len(assets)} investable ETFs")
        axes[0].set_title(f"Sample vs Ledoit–Wolf covariance — {period} · no strategy performance")
        name = f"2_2_{period}_diagnostics.png"
        fig.savefig(RESULTS / name, dpi=160); plt.close(fig); generated.append(name)
        for name in generated:
            manifest["files"][name] = {"sha256": sha256_file(RESULTS / name)}
        pairwise = corr.loc[config["tickers"]["sectors"], config["tickers"]["sectors"]].to_numpy()
        manifest["periods"][period] = {"first_session": str(start.date()),
            "last_session": str(end.date()), "sessions": len(returns),
            "covariance_dates": len(dates), "first_estimate": str(dates.min().date()),
            "last_estimate": str(dates.max().date()),
            "mean_sector_pair_correlation": float(pairwise[np.triu_indices(len(pairwise), 1)].mean()),
            "negative_rolling_share": {c: float(rolling[c].dropna().lt(0).mean()) for c in rolling},
            "median_condition_number": diagnostics.condition_number.groupby(level="estimator").median().to_dict()}
        print(period, json.dumps(manifest["periods"][period], indent=2))
    (RESULTS / "2_1b_2_2_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
