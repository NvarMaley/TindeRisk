"""Reproduce Chapter 3's synthetic comparison and pitch figure."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from .adaptive_simulation import compare_designs
from .paths import RESULTS, ROOT


def main():
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    scenarios = {"reference": {}, "high noise": {"sharpness": 55.},
                 "different thresholds": {"cutoff_shift": .55}}
    frames = []
    for scenario, params in scenarios.items():
        result = compare_designs(seed=config["seed"], reference_sharpe=config["reference_sharpe"],
                                 **params)
        frames.append(result.assign(scenario=scenario))
    table = pd.concat(frames, ignore_index=True)
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "3_9_adaptive_comparison.csv", index=False)
    figure, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    reference = table[table["scenario"].eq("reference")]
    for design, group in reference.groupby("design"):
        if design == "whole bank":
            ax.axhline(group["rmse_log_phi"].iloc[0], linestyle="--", color="gray",
                       label="Whole-bank reference (44 informative cards)")
        else:
            ax.plot(group["informative_cards"], group["rmse_log_phi"], label=design.capitalize())
    ax.set(xlabel="Informative cards answered", ylabel="RMSE of log risk aversion",
           title="Risk aversion estimates on 1,000 simulated profiles")
    ax.legend()
    figure.savefig(RESULTS / "3_9_simulated_error.png", dpi=160)
    plt.close(figure)
    print(table[table["informative_cards"].isin([6, 15, 44])].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
