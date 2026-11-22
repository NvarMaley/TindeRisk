"""Model-based planning sensitivity, in original units of monthly paired gain."""

import csv
from pathlib import Path
from statistics import NormalDist

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRIALS = 10000
RHO = 0.3
N = 12


def ar_mean_sd(months):
    return np.sqrt(
        (months + 2 * sum((months - k) * RHO**k for k in range(1, months))) / months**2
    )


def experiment(rng, candidates, sd, gain, validation_months, history_months):
    # Joint Gaussian means of consecutive AR(1) monthly gain series, stationary variance sd².
    # The two candidates share half of their shocks. The registered historical
    # replay separates selection and final evaluation; the gap is history_months.
    cross = (
        RHO ** (history_months + 1)
        * (1 - RHO**validation_months)
        * (1 - RHO**N)
        / ((1 - RHO) ** 2 * validation_months * N)
    )
    covariance = [
        [ar_mean_sd(validation_months) ** 2, cross],
        [cross, ar_mean_sd(N) ** 2],
    ]
    shared = rng.multivariate_normal([0, 0], covariance, size=(TRIALS, 1))
    own = rng.multivariate_normal([0, 0], covariance, size=(TRIALS, candidates))
    noise = sd * (shared + own) / np.sqrt(2)
    se = sd * ar_mean_sd(N)
    critical = NormalDist().inv_cdf(1 - 0.05 / 7)
    rates = []
    for effect in [0.0, gain]:
        means = noise.copy()
        means[:, 0, :] += effect
        chosen = means[:, :, 0].argmax(axis=1)
        held = means[np.arange(TRIALS), chosen, 1]
        rates.append(np.mean(held > critical * se))
    return *rates, 2 * NormalDist().inv_cdf(0.975) * se


if __name__ == "__main__":
    rng = np.random.default_rng(1201)
    with (ROOT / "research/studies.csv").open() as f:
        for row in csv.DictReader(f):
            months, gap = {
                "ETF": (48, 83),
                "MACRO": (48, 83),
                "WRDS": (60, 95),
                "SENT": (24, 0),
            }[row["calendar"]]
            values = experiment(
                rng,
                len(row["challengers"].split("|")),
                float(row["assumed_sd"]),
                float(row["minimum_gain"]),
                months,
                gap,
            )
            print(row["id"], *(f"{x:.6f}" for x in values))
