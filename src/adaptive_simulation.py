"""Synthetic comparison of adaptive, random, fixed and whole-bank designs."""

import numpy as np
import pandas as pd

from .adaptive_profile import DEFAULT_SHARPNESS, AversionPosterior, card_model
from .adaptive_session import VarianceSelector
from .questionnaire import load_question_bank


def simulate_clients(count: int = 1000, seed: int = 42, *,
                     sharpness: float = DEFAULT_SHARPNESS,
                     cutoff_shift: float = 0.) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Draw true log-aversion, a capacity scenario, and paired noisy responses."""
    if count < 1:
        raise ValueError("client count must be positive")
    rng = np.random.default_rng(seed)
    truth = rng.uniform(np.log(.5), np.log(20), count)
    capacity = rng.choice([.03, .04, .06, .08, .10, .12, .15], size=count)
    responses = {}
    for card in load_question_bank():
        if card["bloc"] in ("B", "C"):
            choices, probabilities = card_model(truth, card, sharpness, cutoff_shift)
            draws = rng.random(count)
            indices = (draws > np.cumsum(probabilities, axis=0)[:-1]).sum(axis=0)
            responses[card["id"]] = np.asarray(choices)[indices]
    return truth, capacity, responses


def compare_designs(count: int = 1000, seed: int = 42, *,
                    sharpness: float = DEFAULT_SHARPNESS, cutoff_shift: float = 0.,
                    reference_sharpe: float = .35) -> pd.DataFrame:
    """Score all designs on the same clients, using an unchanged fitted model."""
    truth, capacity, responses = simulate_clients(count, seed, sharpness=sharpness,
                                                   cutoff_shift=cutoff_shift)
    rng = np.random.default_rng(seed + 1)
    prior = AversionPosterior.prior()
    selector = VarianceSelector(prior.theta, load_question_bank())
    b = [key for key in selector.ids if key.startswith("B")]
    c = [key for key in selector.ids if key.startswith("C")]
    fixed = [key for pair in zip(b[::2], c[::3]) for key in pair][:15]
    truth_target = np.minimum(reference_sharpe / np.exp(truth), capacity)
    boundaries = [.04, .06, .09, .12]
    truth_bands = np.searchsorted(boundaries, truth_target, side="right")
    metrics = {}

    for index in range(count):
        random_order = rng.permutation(selector.ids)[:15]
        for design in ("adaptive", "random", "fixed", "whole bank"):
            if design == "whole bank":
                order = selector.ids
            else:
                order = {"adaptive": range(15), "random": random_order, "fixed": fixed}[design]
            posterior = prior
            asked = {}
            for step, key in enumerate(order, 1):
                if design == "adaptive":
                    # Reserve early slots for both response formats.
                    allowed = ("B",) if step in (2, 4) else ("C",) if step in (1, 3) else ("B", "C")
                    key = selector.choose(posterior, asked, allowed)["id"]
                answer = responses[key][index]
                asked[key] = answer
                posterior = selector.observe(posterior, key, answer)
                if design == "whole bank" and step != len(selector.ids):
                    continue
                median = float(np.interp(.5, np.cumsum(posterior.mass), posterior.theta))
                estimate = min(reference_sharpe / np.exp(median), capacity[index])
                band = np.searchsorted(boundaries, estimate, side="right")
                accumulator = metrics.setdefault((design, step), np.zeros(3))
                accumulator += [(median - truth[index])**2, abs(estimate - truth_target[index]),
                                band == truth_bands[index]]
    return pd.DataFrame([
        {"design": design, "informative_cards": step,
         "rmse_log_phi": np.sqrt(values[0] / count),
         "target_mae_pp": values[1] * 100 / count, "category_accuracy": values[2] / count}
        for (design, step), values in metrics.items()
    ])
