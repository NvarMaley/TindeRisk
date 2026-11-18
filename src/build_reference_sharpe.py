"""Generate the descriptive evidence and profiling sensitivity for step 2.4."""

import json
from itertools import product

import pandas as pd
import yaml

from .paths import ROOT, RESULTS, PROCESSED_DATA
from .profiling import assign_risk_band, category_from_profile, tolerance_volatility
from .provenance import sha256_file


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    baseline = config["reference_sharpe"]
    source_path = RESULTS / "2_1_manifest.json"
    source = json.loads(source_path.read_text())
    sample_path = PROCESSED_DATA / "common_sample_manifest.json"
    if sha256_file(sample_path) != source["sample_manifest_sha256"]:
        raise ValueError("common sample changed; rerun src.build_descriptive")

    evidence = []
    for period in config["validation"]["periods"]:
        path = RESULTS / f"2_1_{period}_descriptive_stats.csv"
        if sha256_file(path) != source["files"][path.name]["sha256"]:
            raise ValueError(f"descriptive checksum mismatch: {path.name}")
        stats = pd.read_csv(path, index_col="asset")
        for asset in (config["benchmark"], "IEF", "60/40"):
            evidence.append({"period": period, "reference": asset,
                             **source["periods"][period],
                             "historical_gross_sharpe": stats.loc[asset, "sharpe"]})

    # Use Raf's scenario grid for comparability.
    scenarios = []
    for phi, sharpe in product((1, 1.5, 2, 3, 4, 6, 8, 12),
                               sorted({.25, .30, baseline, .40, .50})):
        tolerance = tolerance_volatility(phi, sharpe)
        effective, band = category_from_profile(tolerance, .08)
        scenarios.append({"risk_aversion": phi, "reference_sharpe": sharpe,
                          "is_baseline": sharpe == baseline,
                          "tolerance_volatility": tolerance,
                          "tolerance_band": assign_risk_band(tolerance).key,
                          "illustrative_capacity": .08, "capped_volatility": effective,
                          "capped_band": band.key})

    tables = {"2_4_reference_sharpe_evidence.csv": pd.DataFrame(evidence),
              "2_4_sigma_star_sensitivity.csv": pd.DataFrame(scenarios)}
    for name, table in tables.items():
        if table.isin([float("inf"), float("-inf")]).any().any() or table.isna().any().any():
            raise ValueError(f"nonfinite result in {name}")
    for name, table in tables.items():
        table.to_csv(RESULTS / name, index=False)
    manifest = {"reference_sharpe": baseline, "config_sha256": sha256_file(config_path),
                "descriptive_manifest_sha256": sha256_file(source_path),
                "scope": "profiling calibration, descriptive gross Sharpe, illustrative capacity",
                "files": {name: sha256_file(RESULTS / name) for name in tables}}
    (RESULTS / "2_4_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
