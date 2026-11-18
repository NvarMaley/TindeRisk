"""Reproduce step 2.3: python -m src.build_expected_returns."""

import json
from datetime import UTC, datetime
from importlib.metadata import version

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .expected_returns import rolling_expected_returns
from .paths import ROOT, PROCESSED_DATA, RESULTS
from .provenance import sha256_file


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    settings = config["expected_returns"]
    required = {"method": "regularized_bayes_stein", "target": "gmv_mean",
                "covariance": "lw_constcorr", "units": "annualized_excess_arithmetic"}
    if any(settings.get(key) != value for key, value in required.items()):
        raise ValueError("unsupported expected-return configuration")
    sample_path = PROCESSED_DATA / "common_sample_manifest.json"
    sample = json.loads(sample_path.read_text())
    excess_path = PROCESSED_DATA / "excess_returns.parquet"
    if sha256_file(excess_path) != sample["inputs"]["excess_returns"]:
        raise ValueError("excess return source checksum mismatch")
    excess = pd.read_parquet(excess_path)
    if not excess.index.is_unique or not excess.index.is_monotonic_increasing:
        raise ValueError("excess source dates must be sorted and unique")
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    universe = assets + [config["benchmark"]]
    if list(excess.columns) != universe:
        raise ValueError("excess source universe differs from config")
    window = 252 * config["portfolio"]["estimation_window_years"]
    manifest = {"created_utc": datetime.now(UTC).isoformat(),
        "scope": "2.3 implementation diagnostics; no predictive validation or strategy ranking",
        "settings": settings, "config_sha256": sha256_file(config_path),
        "sample_manifest_sha256": sha256_file(sample_path),
        "source_excess_sha256": sha256_file(excess_path),
        "runtime_versions": {name: version(name) for name in ["numpy", "pandas", "matplotlib"]},
        "window_sessions": window, "annualization": 252,
        "covariance_input": "simple asset returns, daily LW constant correlation",
        "mean_input": "daily excess return using existing same-date DTB3 proxy; timing gate unresolved",
        "timing": "completed NYSE month-end close; usable only afterward",
        "target_note": "unconstrained GMV-mean target, not the BL ERC anchor or a tradable strategy",
        "holdout_status": "not frozen; legacy notebook already explored future-return comparisons",
        "files": {}, "periods": {}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    for period in config["validation"]["periods"]:
        frames = {}
        for key in ["returns", "warmup_returns"]:
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != sample["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            frames[key] = pd.read_parquet(path)
            if list(frames[key].columns) != universe:
                raise ValueError("common sample universe differs from config")
        history = pd.concat([frames["warmup_returns"], frames["returns"]])[assets]
        start, end = frames["returns"].index.min(), frames["returns"].index.max()
        schedule = mcal.get_calendar("NYSE").valid_days(
            start.replace(day=1), end + pd.offsets.MonthEnd(0), tz=None)
        month_ends = pd.Series(schedule, index=schedule).groupby(schedule.to_period("M")).last()
        dates = pd.DatetimeIndex(month_ends[month_ends.isin(frames["returns"].index)])
        aligned_excess = excess.reindex(history.index)[assets]
        mu, raw, diagnostics = rolling_expected_returns(history, aligned_excess, dates, window)
        outputs = {f"2_3_{period}_mu.csv": mu, f"2_3_{period}_raw_mean_control.csv": raw,
                   f"2_3_{period}_diagnostics.csv": diagnostics}
        for name, table in outputs.items():
            table.to_csv(RESULTS / name)
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout="constrained")
        latest = pd.DataFrame({"Raw mean (control only)": raw.iloc[-1],
                               "Regularized Bayes–Stein": mu.iloc[-1]})
        latest.plot.bar(ax=axes[0], rot=45)
        axes[0].yaxis.set_major_formatter(PercentFormatter(1))
        axes[0].axhline(0, color="gray", linewidth=.8)
        axes[0].set_ylabel("Annual arithmetic excess mean")
        axes[0].set_title(f"Historical mean estimates at {mu.index[-1].date()} — {period}")
        diagnostics.shrinkage.plot(ax=axes[1], color="#1f77b4")
        axes[1].set_ylim(0, 1); axes[1].set_ylabel("Mean shrinkage intensity")
        axes[1].set_xlabel(f"Month-end close · {window} trailing sessions · not a promised return")
        figure_name = f"2_3_{period}_diagnostics.png"
        fig.savefig(RESULTS / figure_name, dpi=160)
        plt.close(fig)
        for name in [*outputs, figure_name]:
            manifest["files"][name] = {"sha256": sha256_file(RESULTS / name)}
        manifest["periods"][period] = {"estimation_dates": len(mu),
            "first_estimate": str(mu.index.min().date()), "last_estimate": str(mu.index.max().date()),
            "mean_shrinkage": float(diagnostics.shrinkage.mean()),
            "min_shrinkage": float(diagnostics.shrinkage.min()),
            "max_shrinkage": float(diagnostics.shrinkage.max()),
            "all_dispersion_reduced": bool(np.all(diagnostics.shrunk_cross_sectional_std <=
                                                  diagnostics.raw_cross_sectional_std + 1e-14))}
        print(period, json.dumps(manifest["periods"][period], indent=2))
    (RESULTS / "2_3_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
