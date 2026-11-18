"""Step 2.6 distribution and subperiod diagnostics for assets and baselines."""

import json

import pandas as pd
import yaml

from .descriptive import descriptive_statistics
from .paths import PROCESSED_DATA, RESULTS, ROOT
from .provenance import sha256_file

# Fixed calendar boundaries shared across both samples, with exclusive ends.
SUBPERIODS = (
    ("Through 2019", None, "2020-01-01"),
    ("2020–2021", "2020-01-01", "2022-01-01"),
    ("2022 onward", "2022-01-01", None),
)
BASELINES = ("Equal weight", "GMV", "60/40")


def subperiod_diagnostics(returns: pd.DataFrame, risk_free: pd.Series) -> pd.DataFrame:
    """Report full sample and disjoint calendar blocks with observed coverage."""
    if not returns.index.equals(risk_free.index):
        raise ValueError("risk-free dates must exactly match return dates")

    results = []
    for label, start, stop in (("Full sample", None, None), *SUBPERIODS):
        dates = returns.index
        if start is not None:
            dates = dates[dates >= pd.Timestamp(start)]
        if stop is not None:
            dates = dates[dates < pd.Timestamp(stop)]
        if not len(dates):
            continue
        panel = returns.loc[dates]
        if len(panel) < 12:
            # Retain coverage for a short block without running lag-10 tests.
            metrics = pd.DataFrame(index=panel.columns.rename("asset"))
        else:
            metrics = descriptive_statistics(panel, risk_free.loc[dates])
        metrics = metrics.assign(subperiod=label, first_session=dates[0],
                                 last_session=dates[-1], sessions=len(dates))
        metrics["tail_sessions"] = (
            panel.le(panel.quantile(.05)).sum() if len(panel) >= 12 else pd.NA
        )
        results.append(metrics.reset_index(names="series"))
    if not results:
        raise ValueError("no return observations")
    return pd.concat(results, ignore_index=True)


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    common_path = PROCESSED_DATA / "common_sample_manifest.json"
    common = json.loads(common_path.read_text())
    baseline_path = RESULTS / "2_5_manifest.json"
    baseline = json.loads(baseline_path.read_text())
    input_hashes = {"common_sample_manifest_sha256": sha256_file(common_path),
                    "config_sha256": sha256_file(config_path)}
    if any(baseline[key] != digest for key, digest in input_hashes.items()):
        raise ValueError("baseline inputs changed; rerun src.build_baselines")

    tables = []
    for period in config["validation"]["periods"]:
        frames = {}
        for key in ("returns", "rf_daily"):
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != common["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            frames[key] = pd.read_parquet(path)
        path = RESULTS / f"2_5_{period}_returns.csv"
        if sha256_file(path) != baseline["files"][path.name]:
            raise ValueError(f"baseline checksum mismatch: {path.name}")
        history = pd.read_csv(path, index_col=0, header=[0, 1], parse_dates=True)
        assets = frames["returns"]
        if not history.index.equals(assets.index):
            raise ValueError("asset and baseline dates must match")
        portfolios = history.xs("gross_return", level=1, axis=1).loc[:, list(BASELINES)]

        for kind, panel in (("asset", assets), ("baseline", portfolios)):
            table = subperiod_diagnostics(panel, frames["rf_daily"]["rf_daily"])
            tables.append(table.assign(period=period, kind=kind))

    path = RESULTS / "2_6_diagnostics.csv"
    pd.concat(tables, ignore_index=True).to_csv(path, index=False)
    manifest = {**input_hashes, "baselines_manifest_sha256": sha256_file(baseline_path),
                "calendar_blocks": SUBPERIODS, "tail_probability": .05,
                "files": {path.name: sha256_file(path)}}
    (RESULTS / "2_6_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
