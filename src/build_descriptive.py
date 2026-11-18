"""Reproduce Step 2.1 on the main/extended common samples, without ranking strategies."""

import json
from datetime import UTC, datetime
from importlib.metadata import version

import pandas as pd
import yaml

from .descriptive import descriptive_statistics
from .paths import ROOT, PROCESSED_DATA, RESULTS
from .provenance import sha256_file


def main():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    sample_manifest = json.loads((PROCESSED_DATA / "common_sample_manifest.json").read_text())
    manifest = {"created_utc": datetime.now(UTC).isoformat(),
                "scope": "historical asset diagnostics, gross of trading costs; not strategy performance or forecasts",
                "reference": "60/40 is daily rebalanced for this descriptive table only; monthly baseline remains Step 2.5",
                "changes_from_raf": "include initial wealth in drawdown; use common completed-session periods; guard constant series",
                "sample_manifest_sha256": sha256_file(PROCESSED_DATA / "common_sample_manifest.json"),
                "runtime_versions": {name: version(name) for name in ["numpy", "pandas", "scipy", "statsmodels"]},
                "files": {}, "periods": {}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    for period in config["validation"]["periods"]:
        paths = {key: PROCESSED_DATA / f"common_{period}_{key}.parquet" for key in ["returns", "rf_daily"]}
        for path in paths.values():
            if sha256_file(path) != sample_manifest["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
        returns = pd.read_parquet(paths["returns"])
        rf = pd.read_parquet(paths["rf_daily"])["rf_daily"]
        returns["60/40"] = .6*returns[config["benchmark"]] + .4*returns["IEF"]
        table = descriptive_statistics(returns, rf)
        path = RESULTS / f"2_1_{period}_descriptive_stats.csv"
        table.to_csv(path)
        manifest["files"][path.name] = {"sha256": sha256_file(path), "shape": list(table.shape)}
        manifest["periods"][period] = {"start": str(returns.index.min().date()),
                                       "end": str(returns.index.max().date()), "sessions": len(returns)}
        print(period, manifest["periods"][period])
        print(table[["ann_return", "ann_vol", "sharpe", "max_drawdown"]].round(4).to_string())
    (RESULTS / "2_1_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
