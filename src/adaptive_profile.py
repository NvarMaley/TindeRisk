"""Likelihoods and posterior updates for the experimental adaptive path."""

from dataclasses import dataclass

import numpy as np
from scipy.special import expit
from scipy.stats import norm


# Starting assumptions for simulation, in log-aversion units.
ORDERED_PRIORS = {
    "reaction": (1.1, .05),
    "loss_comfort": (1.2, 0.),
    "risk_mix": (1., -.05),
    "tradeoff": (1.2, .10),
}
DEFAULT_SHARPNESS = 180.0


def swipe_probabilities(theta, card: dict, sharpness: float = DEFAULT_SHARPNESS) -> np.ndarray:
    """Rows are canonical A/B, independent of which option is displayed first."""
    a, b = (card["options"][key] for key in ("A", "B"))
    if not np.isfinite(sharpness) or sharpness <= 0:
        raise ValueError("swipe sharpness must be positive and finite")
    delta = (b["mu"] - a["mu"]) - .5 * np.exp(theta) * (b["sigma"]**2 - a["sigma"]**2)
    return np.array([expit(-sharpness * delta), expit(sharpness * delta)])


def ordered_probabilities(theta, discrimination: float, cutoffs) -> np.ndarray:
    """Rows are ordered from less to more willingness to accept risk."""
    cutoffs = np.asarray(cutoffs, dtype=float)
    if (not np.isfinite(discrimination) or discrimination <= 0 or cutoffs.shape != (3,)
            or not np.isfinite(cutoffs).all() or not (np.diff(cutoffs) < 0).all()):
        raise ValueError("ordered model requires a positive slope and three descending cutoffs")
    theta = np.atleast_1d(theta)
    exceed = expit(discrimination * (cutoffs[:, None] - theta))
    return np.vstack((1 - exceed[0], exceed[:-1] - exceed[1:], exceed[-1]))


def card_model(theta: np.ndarray, card: dict, sharpness: float = DEFAULT_SHARPNESS,
               cutoff_shift: float = 0.) -> tuple[tuple[str, ...], np.ndarray]:
    """Return canonical response IDs and likelihood rows for a B or C card."""
    if card["bloc"] == "C":
        return ("A", "B"), swipe_probabilities(theta, card, sharpness)
    if card["bloc"] != "B":
        raise ValueError("only tolerance cards provide likelihoods")
    slope, offset = ORDERED_PRIORS[card["params"]["theme"]]
    cutoffs = np.log(3.) + offset + cutoff_shift + np.array([.8, 0., -.8])
    return tuple(card["params"]["ordered_option_ids"]), ordered_probabilities(theta, slope, cutoffs)


@dataclass(frozen=True)
class AversionPosterior:
    theta: np.ndarray
    mass: np.ndarray

    @classmethod
    def prior(cls) -> "AversionPosterior":
        grid = np.linspace(np.log(.3), np.log(30), 200)
        weights = norm.pdf(grid, loc=np.log(3.), scale=1.1)
        return cls(grid, weights / weights.sum())

    def update(self, likelihood: np.ndarray | None) -> "AversionPosterior":
        """Condition on one observation. A skip leaves the distribution intact."""
        if likelihood is None:
            return self
        likelihood = np.asarray(likelihood, dtype=float)
        if (likelihood.shape != self.mass.shape or not np.isfinite(likelihood).all()
                or (likelihood < 0).any() or (likelihood > 1).any()):
            raise ValueError("invalid likelihood on the aversion grid")
        result = self.mass * likelihood
        total = result.sum()
        if total <= 0:
            raise ValueError("answer has zero probability on the aversion grid")
        return AversionPosterior(self.theta, result / total)

    def summary(self) -> dict:
        mean = float(self.mass @ self.theta)
        spread = float(np.sqrt(self.mass @ (self.theta - mean)**2))
        lower, median, upper = np.interp([.1, .5, .9], np.cumsum(self.mass), self.theta)
        return {"theta_mean": mean, "theta_median": float(median), "theta_sd": spread,
                "phi_median": float(np.exp(median)),
                "phi_ci80": [float(np.exp(lower)), float(np.exp(upper))]}
