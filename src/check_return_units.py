"""Audit Step 2.7 on the two prepared common samples, offline."""

import json

import numpy as np
import pandas as pd
import yaml

from .descriptive import descriptive_statistics
from .estimation import ledoit_wolf_constant_corr, sample_cov
from .paths import PROCESSED_DATA, RESULTS, ROOT
from .provenance import sha256_file

SESSIONS_PER_YEAR = 252


def check_return_units(simple: pd.DataFrame, log: pd.DataFrame,
                       excess: pd.DataFrame, cash: pd.Series) -> dict[str, int | float]:
    """Check stored daily returns and the project's annual risk conversions."""
    for name, panel in (("log", log), ("excess", excess)):
        if not simple.index.equals(panel.index) or not simple.columns.equals(panel.columns):
            raise ValueError(f"{name} returns must align exactly with simple returns")
    if not simple.index.equals(cash.index):
        raise ValueError("cash rates must align exactly with simple returns")
    if any(not np.isfinite(data.to_numpy()).all() for data in (simple, log, excess, cash)):
        raise ValueError("return and cash inputs must be finite")

    annual = SESSIONS_PER_YEAR
    metrics = descriptive_statistics(simple, cash, annualize=annual)
    np.testing.assert_allclose(np.expm1(log), simple, rtol=0, atol=1e-12, err_msg="simple/log identity")
    np.testing.assert_allclose(excess + cash.to_numpy()[:, None], simple, rtol=0, atol=1e-12,
                               err_msg="simple/excess identity")
    np.testing.assert_allclose(metrics["ann_return"], np.expm1(log.sum() * annual / len(log)),
                               rtol=0, atol=1e-12, err_msg="annualized geometric return")

    values = simple.to_numpy()
    daily_std = values.std(axis=0, ddof=1)
    expected_vol = daily_std * np.sqrt(annual)
    np.testing.assert_allclose(metrics["ann_vol"], expected_vol, rtol=1e-12, atol=0)
    annual_cov = sample_cov(simple, annual)
    np.testing.assert_allclose(np.diag(annual_cov), expected_vol**2, rtol=1e-12, atol=0)
    daily_lw, daily_shrinkage = ledoit_wolf_constant_corr(simple, annualize=1)
    annual_lw, annual_shrinkage = ledoit_wolf_constant_corr(simple, annualize=annual)
    np.testing.assert_allclose(annual_lw, daily_lw * annual, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(annual_shrinkage, daily_shrinkage, rtol=0, atol=1e-15)

    # Divide annual arithmetic excess mean by annual volatility and compare
    # with Step 2.1's Sharpe computed directly from daily observations.
    expected_sharpe = excess.to_numpy().mean(axis=0) * annual / expected_vol
    np.testing.assert_allclose(metrics["sharpe"], expected_sharpe, rtol=1e-12, atol=1e-12)

    weights = np.full(simple.shape[1], 1 / simple.shape[1])
    projected_vol = float(np.sqrt(weights @ annual_cov.to_numpy() @ weights))
    realized_vol = float((values @ weights).std(ddof=1) * np.sqrt(annual))
    np.testing.assert_allclose(projected_vol, realized_vol, rtol=1e-12, atol=0)
    return {
        "sessions": len(simple),
        "assets": simple.shape[1],
        "daily_asset_observations": simple.size,
        "max_log_round_trip_error": float(np.max(np.abs(np.expm1(log.to_numpy()) - values))),
        "max_excess_round_trip_error": float(np.max(np.abs(excess.to_numpy() + cash.to_numpy()[:, None] - values))),
        "equal_weight_annual_variance": projected_vol**2,
        "equal_weight_annual_volatility": projected_vol,
    }


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    manifest_path = PROCESSED_DATA / "common_sample_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    report = {"sessions_per_year": SESSIONS_PER_YEAR,
              "common_sample_manifest_sha256": sha256_file(manifest_path), "periods": {}}
    for period in config["validation"]["periods"]:
        frames = {}
        for key in ("returns", "log_returns", "excess_returns", "rf_daily"):
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != manifest["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            frames[key] = pd.read_parquet(path)
        report["periods"][period] = check_return_units(
            frames["returns"], frames["log_returns"], frames["excess_returns"],
            frames["rf_daily"]["rf_daily"],
        )
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "2_7_return_units.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
