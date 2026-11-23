"""Paired client utility using the same two-year moving-block rule as chapter 7."""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def compare(expanded):
    legacy = pd.read_csv(ROOT / "research/execution/results/cohorts.csv")
    current = pd.read_csv(expanded)
    keys = ["case", "policy", "cohort"]
    samples = [
        frame.pivot(index=keys, columns="arm", values="net_household_return")
        for frame in (legacy, current)
    ]
    if not samples[0].index.equals(samples[1].index):
        raise ValueError("Unmatched cohorts")
    joint = samples[0].join(samples[1], lsuffix="_3", rsuffix="_13")
    rows = []
    for (case, policy), g in joint.groupby(level=["case", "policy"]):
        n = len(g)
        starts = np.random.default_rng(7201).integers(n - 1, size=(3999, (n + 1) // 2))
        idx = (starts[:, :, None] + np.arange(2)).reshape(3999, -1)[:, :n]
        for arm in ("classical", "robust"):
            a = g[arm + "_13"].to_numpy()
            for ref in ("60/40_13", arm + "_3"):
                b = g[ref].to_numpy()
                for phi in (8 / 3, 40 / 9):

                    def score(v):
                        return v.mean(axis=-1) - phi * v.var(axis=-1, ddof=1) / 2

                    low, high = np.quantile(
                        score(a[idx]) - score(b[idx]), [0.025, 0.975]
                    )
                    rows.append(
                        dict(
                            case=case,
                            policy=policy,
                            arm=arm,
                            reference=ref,
                            years=n,
                            phi=phi,
                            gain=score(a) - score(b),
                            low=low,
                            high=high,
                            independent_years=0,
                        )
                    )
    return pd.DataFrame(rows)
