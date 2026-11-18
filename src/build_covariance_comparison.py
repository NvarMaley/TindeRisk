"""Regenerate Step 2.8 from the verified common samples and Step 2.5 targets."""

import json

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .covariance_comparison import compare_covariances
from .paths import PROCESSED_DATA, RESULTS, ROOT
from .provenance import sha256_file


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    common_path = PROCESSED_DATA / "common_sample_manifest.json"
    baseline_path = RESULTS / "2_5_manifest.json"
    common = json.loads(common_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    inputs = {"common_sample_manifest_sha256": sha256_file(common_path),
              "config_sha256": sha256_file(config_path)}
    if any(baseline[key] != value for key, value in inputs.items()):
        raise ValueError("baseline inputs changed; rerun src.build_baselines")
    window = baseline["window_sessions"]
    cap = baseline["gmv_weight_cap"]
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    calendar = mcal.get_calendar("NYSE")
    manifest = {**inputs, "baselines_manifest_sha256": sha256_file(baseline_path),
                "window_sessions": window, "gmv_weight_cap": cap, "files": {}}
    summaries = []
    for period in config["validation"]["periods"]:
        panels = {}
        for key in ("warmup_returns", "returns"):
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != common["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            panels[key] = pd.read_parquet(path)[assets]
        target_path = RESULTS / f"2_5_{period}_targets.csv"
        if sha256_file(target_path) != baseline["files"][target_path.name]:
            raise ValueError(f"baseline checksum mismatch: {target_path.name}")
        existing = pd.read_csv(target_path, index_col=[0, 1], parse_dates=[1]).loc["GMV", assets]
        returns = panels["returns"]
        history = pd.concat([panels["warmup_returns"], returns])
        last = returns.index[-1]
        final_close = calendar.valid_days(last, last + pd.offsets.MonthEnd(0), tz=None)[-1]
        rows, weights = compare_covariances(history, returns, existing.index, final_close, window, cap)
        np.testing.assert_allclose(weights.loc["lw_constcorr"], existing, rtol=0, atol=1e-9)

        complete = rows[rows["complete_month"]].reset_index()
        paired = weights.loc["sample"].sub(weights.loc["lw_constcorr"])
        complete_dates = complete["decision_close"].unique()
        mean_distance = paired.loc[complete_dates].abs().sum(axis=1).mean() / 2
        summary = complete.groupby("estimator").agg(
            months=("vol_error", "count"), turnover_events=("turnover_two_way", "count"),
            median_condition_number=("condition_number", "median"),
            mean_turnover_two_way=("turnover_two_way", "mean"),
            mean_predicted_vol=("predicted_vol", "mean"), mean_realized_vol=("realized_vol", "mean"),
            signed_vol_bias=("vol_error", "mean"),
            vol_mae=("vol_error", lambda error: error.abs().mean()),
            vol_rmse=("vol_error", lambda error: np.sqrt(error.pow(2).mean())),
        )
        summaries.append(summary.assign(period=period, mean_target_weight_distance=mean_distance))
        for suffix, table in (("monthly", rows), ("weights", weights), ("sample_minus_lw_weights", paired)):
            path = RESULTS / f"2_8_{period}_{suffix}.csv"
            table.to_csv(path)
            manifest["files"][path.name] = sha256_file(path)
    path = RESULTS / "2_8_summary.csv"
    pd.concat(summaries).to_csv(path)
    manifest["files"][path.name] = sha256_file(path)
    (RESULTS / "2_8_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
