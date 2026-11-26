"""Portable course experiment using RiskMatch's constrained optimizer."""
import numpy as np

from riskmatch.optimization.mean_variance import Constraints, MeanVariance

ASSETS = ("Actions US", "Trésor court terme", "Trésor intermédiaire", "Immobilier coté", "Liquidités")
SHOCKS = {
    "Krach actions": (-.40, .02, .04, -.30, 0.),
    "Inflation et taux": (-.18, -.02, -.12, -.25, 0.),
    "Récession": (-.25, .01, .08, -.35, 0.),
}
FEE = .001


def sample():
    """Monthly decimal total returns generated from a fixed seed, 96 + 24 months."""
    rng = np.random.default_rng(12)
    independent = rng.normal(size=(120, 5))
    loadings = np.array([
        [.039, 0., 0., 0., 0.],
        [-.002, .005, 0., 0., 0.],
        [-.005, .012, .015, 0., 0.],
        [.023, -.004, 0., .035, 0.],
        [0., 0., 0., 0., .00015],
    ])
    noise = independent @ loadings.T
    # Fix training means so the demonstration is reproducible even if the random noise changes.
    noise[:96] -= noise[:96].mean(axis=0)
    months = noise + np.array([.010, .0034, .004, .007, .002])
    return months[:96], months[96:]


def calculate(stress_limit, aversion, position_cap, allowed):
    train, _ = sample()
    means = 12 * train.mean(axis=0)
    covariance = 12 * np.cov(train, rowvar=False)
    upper = np.where(allowed, position_cap, 0.)
    rows = [(name, np.array(shock), -stress_limit, 1.) for name, shock in SHOCKS.items()]
    engine = MeanVariance(means, covariance, means[-1], Constraints(np.zeros(len(ASSETS)), upper, linear=rows))
    utility = engine.solve(return_weight=1., variance_weight=aversion)
    defensive = engine.solve()
    if utility["status"] != "optimal" or defensive["status"] != "optimal":
        return None
    return {"utility": np.asarray(utility["weights"]), "defensive": np.asarray(defensive["weights"]),
            "means": means, "covariance": covariance}


def metrics(weights, means, covariance):
    shocks = {name: float(weights @ shock) for name, shock in SHOCKS.items()}
    return {"return": float(weights @ means), "volatility": float(np.sqrt(weights @ covariance @ weights)),
            "loss": max(0., -min(shocks.values())), "shocks": shocks}


def holdout(weights):
    """Buy and hold in the 24 untouched months, with one initial trading fee."""
    _, test = sample()
    capital_after_fees = 1 / (1 + FEE * sum(weights[:-1]))
    return np.r_[1., capital_after_fees * (np.cumprod(1 + test, axis=0) @ weights)]
