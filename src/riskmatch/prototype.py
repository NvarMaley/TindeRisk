"""Shared research prototype. All returns are synthetic, never investment advice."""
from dataclasses import dataclass
import numpy as np
from riskmatch.analytics.tail_risk import empirical
from riskmatch.backtesting.baselines import annualized_excess_ratio

ASSETS = ("US equities", "US Treasuries", "US REIT", "USD cash")
VERSION = "synthetic-v1"


@dataclass(frozen=True)
class ClientProfile:
    capital: float
    years: float
    max_stress_loss: float
    currency: str = "USD"

    def __post_init__(self):
        if not np.isfinite([self.capital, self.years, self.max_stress_loss]).all():
            raise ValueError("Non-finite values")
        if self.capital <= 0 or self.years <= 0 or not 0 <= self.max_stress_loss <= 1:
            raise ValueError("Invalid mandate")
        if self.currency != "USD":
            raise ValueError("USD-only prototype")


def cards():
    from riskmatch.behavioral.discovery import session
    return session(0)["cards"]


def score(responses):
    from riskmatch.behavioral.discovery import score as discovery_score
    return discovery_score(0, "USD", responses)


def synthetic_returns(seed=42, n=120):
    rng = np.random.default_rng(seed)
    mean = np.array([.006, .0025, .004, .0015])
    vol = np.array([.045, .02, .05, .0005])
    corr = np.array([[1,.05,.6,0],[.05,1,.1,0],[.6,.1,1,0],[0,0,0,1]])
    return rng.multivariate_normal(mean, np.outer(vol,vol)*corr, size=n)


def metrics(returns, weights, *, cash_returns=None):
    r = returns @ np.asarray(weights)
    nav = np.r_[1, np.cumprod(1+r)]
    dd = nav / np.maximum.accumulate(nav) - 1
    tail = empirical(-r, .95)
    result = dict(cagr=float(nav[-1]**(12/len(r))-1), vol=float(r.std(ddof=1)*np.sqrt(12)),
                  drawdown=float(dd.min()), es95_monthly=tail["es"],
                  nav=[float(x) for x in nav])
    if cash_returns is not None:
        result["sharpe"] = annualized_excess_ratio(r, cash_returns)
    return result


def candidates(profile):
    train, test = np.split(synthetic_returns(), [84])
    # Fixed-weight monthly rebalancing, cost-free, held-out synthetic observations.
    allocations = {"Cash": [0,0,0,1], "Conservative": [.15,.45,0,.4],
                   "60/40": [.6,.4,0,0], "1/N": [.25]*4,
                   "Growth": [.7,.1,.2,0], "Fixed income": [0,.8,0,.2]}
    stress = np.array([-.30,-.12,-.35,0])
    result = []
    for name, w in allocations.items():
        loss = float(-stress @ w)
        if loss <= profile.max_stress_loss + 1e-12:
            result.append(dict(name=name, weights=dict(zip(ASSETS,w)), stress_loss=loss,
                               stress_usd=loss*profile.capital, metrics=metrics(test,w,cash_returns=test[:,3]),
                               period="36 synthetic out-of-calibration months",
                               costs="Not modeled", version=VERSION))
    return result
