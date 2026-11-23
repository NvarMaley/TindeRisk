"""Small scoring controls with known outcomes, independent of the market archive."""

from copy import deepcopy
from .scoring import FAMILIES, rank


def scoring_controls(cfg):
    metrics = dict(
        valid=True,
        tradable=True,
        net=0.07,
        cagr=0.05,
        drawdown=-0.10,
        fee=0.001,
        loss=0.08,
        hhi=0.3,
    )
    signals = {
        k: dict(
            validated=True,
            target="CHF return",
            months=12,
            value=65,
            evidence="fixture",
            version=1,
        )
        for k in FAMILIES
    }
    cards = {
        "A": metrics | dict(signals=signals),
        "B": metrics | dict(net=0.0701, signals=signals),
        "Off-ceiling": metrics | dict(valid=False, net=0.8),
        "Inconnue": metrics | dict(cagr=None),
    }
    criteria = cfg["profiles"]["Goal"]
    registry = [
        {
            "name": family,
            "scope": card,
            "target": "CHF return",
            "horizon": "12 months",
            "issued": cfg["market"],
            "expires": cfg["market"],
            "version": 1,
            "weight": 1.0,
            "status": "approved",
            "score_100": 65,
        }
        for family in FAMILIES
        for card in ["A", "B"]
    ]
    complete = rank(cards, criteria, cfg, registry=registry)
    assert complete["coverage"] == 100 and set(complete["rows"]) == {"A", "B"}
    assert complete["rows"]["A"]["group"] == complete["rows"]["B"]["group"]
    partial = deepcopy(cards)
    partial["A"]["signals"]["sentiment"]["validated"] = False
    no_sentiment = rank(partial, criteria, cfg, registry=registry)
    assert no_sentiment["coverage"] == 90 and all(
        "forecast" not in r["subscores"] for r in no_sentiment["rows"].values()
    )
    partial["A"]["net"] = 0.0702
    reversed_rank = rank(partial, criteria, cfg, registry=registry)
    assert reversed_rank["rows"]["A"]["total"] > reversed_rank["rows"]["B"]["total"]
    return dict(full=complete, missing_sentiment=no_sentiment, reversal=reversed_rank)
