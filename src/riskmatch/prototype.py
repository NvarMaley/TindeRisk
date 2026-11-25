"""Shared research prototype. All returns are synthetic, never investment advice."""
from dataclasses import dataclass
import numpy as np

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
    result = []
    for i in range(8):
        amount = 100 + 50 * i
        result.append(dict(id=f"L{i+1:02}", block="Lotteries", a=f"50% +{amount*2} USD, 50% 0 USD",
                           b=f"+{amount} USD guaranteed", scored=True,
                           fr=dict(block="Loteries", a=f"50% +{amount*2} USD, 50% 0 USD", b=f"+{amount} USD certain")))
    for i in range(6):
        loss = 50 + i * 25
        result.append(dict(id=f"F{i+1:02}", block="Gains / losses",
                           a=f"50% +{loss*2} USD, 50% −{loss} USD", b="0 USD guaranteed", scored=True,
                           fr=dict(block="Gains / pertes", a=f"50% +{loss*2} USD, 50% −{loss} USD", b="0 USD certain")))
    for i in range(6):
        result.append(dict(id=f"D{i+1:02}", block="Drawdown",
                           a=f"Accept a {10+i*5}% decline scenario; recovery uncertain",
                           b="Less volatile allocation, lower growth potential", scored=True,
                           fr=dict(block="Drawdown", a=f"Accepter un scénario de baisse de {10+i*5}% ; récupération incertaine",
                                   b="Allocation moins fluctuante, potentiel inférieur")))
    for i in range(4):
        result.append(dict(id=f"H{i+1:02}", block="Horizon / uncertainty",
                           a=f"{110+i*10} USD in one year", b="100 USD today", scored=False,
                           fr=dict(block="Horizon / incertitude", a=f"{110+i*10} USD dans un an", b="100 USD aujourd'hui")))
        result.append(dict(id=f"P{i+1:02}", block="Preferences",
                           a=f"Adjust allocation every {i+1} month(s)",
                           b="Stable allocation with annual review", scored=False,
                           fr=dict(block="Préférences", a=f"Ajuster l'allocation tous les {i+1} mois",
                                   b="Allocation stable avec révision annuelle")))
    for i in range(2):
        result.append(dict(id=f"C{i+1:02}", block="Consistency",
                           a=result[i]["a"], b=result[i]["b"], scored=False, pair=result[i]["id"],
                           fr=dict(result[i]["fr"], block="Cohérence")))
    return result


def score(responses):
    if not isinstance(responses, dict):
        raise ValueError("Invalid responses")
    allowed = {"like", "dislike", "unsure", "skip"}
    if any(v not in allowed for v in responses.values()):
        raise ValueError("Invalid choice")
    items = [c for c in cards() if c["scored"]]
    valid = [responses.get(c["id"]) for c in items if responses.get(c["id"]) in ("like", "dislike")]
    n, total = len(valid), len(items)
    prudent = valid.count("dislike")
    return dict(score=round(1 + 29*prudent/n) if n/total >= .7 else None,
                coverage=n/total, sensitivity=[round(1+29*prudent/total),
                round(1+29*(prudent+total-n)/total)], version=VERSION,
                inconsistencies=[c["id"] for c in cards() if c.get("pair")
                and responses.get(c["id"]) in ("like","dislike")
                and responses.get(c["pair"]) in ("like","dislike")
                and responses[c["id"]] != responses[c["pair"]]])


def synthetic_returns(seed=42, n=120):
    rng = np.random.default_rng(seed)
    mean = np.array([.006, .0025, .004, .0015])
    vol = np.array([.045, .02, .05, .0005])
    corr = np.array([[1,.05,.6,0],[.05,1,.1,0],[.6,.1,1,0],[0,0,0,1]])
    return rng.multivariate_normal(mean, np.outer(vol,vol)*corr, size=n)


def metrics(returns, weights):
    r = returns @ np.asarray(weights)
    nav = np.r_[1, np.cumprod(1+r)]
    dd = nav / np.maximum.accumulate(nav) - 1
    losses = np.sort(-r)
    tail_n = max(1, int(np.ceil(.05*len(r))))
    return dict(cagr=float(nav[-1]**(12/len(r))-1), vol=float(r.std(ddof=1)*np.sqrt(12)),
                drawdown=float(dd.min()), es95_monthly=float(losses[-tail_n:].mean()),
                nav=[float(x) for x in nav])


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
                               stress_usd=loss*profile.capital, metrics=metrics(test,w),
                               period="36 synthetic out-of-calibration months",
                               costs="Not modeled", version=VERSION))
    return result
