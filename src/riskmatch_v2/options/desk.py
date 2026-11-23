"""Recalculate a historical mandate with a custom range and ticker exclusions."""

from dataclasses import replace
from functools import lru_cache
import numpy as np
from .study import context, cashflows, aggregate_card
from .compare import models, weights, distinct
from .replay import replay
from ..feasibility.engine import Frontier


def research_desk(low, high, excluded, report):
    cfg, params, _, daily, shock, t = context()
    cfg = cfg | dict(risk_low=low, risk_cap=high)

    @lru_cache
    def dated(day):
        ensemble = models(daily.loc[:day], params)
        hi = ensemble[0].hi.copy()
        for name in excluded:
            hi[ensemble[0].names.index(name)] = 0.0
        return [replace(m, hi=hi) for m in ensemble]

    m = dated(cfg["market"])
    r = Frontier(m[0]).solve(low=low, high=high)
    if not r["candidate"]:
        return {
            "reason": r["proof"],
            "status": r["status"],
            "maximum": r["max_risk_bound"],
        }
    targets = weights(m, shock, high, cfg["return_concession"], low)
    unique, aliases = distinct(targets, cfg["duplicate_half_l1"])
    cards, plans, unavailable = {}, {}, {}
    for name, w in unique.items():
        unavailable[name] = []

        def decide(day, current):
            ms = [replace(model, current=current) for model in dated(day)]
            try:
                choices = weights(ms, shock, high, cfg["return_concession"], low)
            except ValueError:
                choices = {}
            if name not in choices:
                unavailable[name].append(day)
                return current
            return choices[name]

        decisions = {
            day: (lambda current, d=day: decide(d, current))
            for day in report["signals"]
        }
        history, _, _, _, plans[name] = replay(
            t,
            decisions,
            cfg["pocket"],
            cfg["reserve"],
            flows=cashflows(),
            risk_cap=high,
        )
        cards[name] = aggregate_card(m, w, shock, history, cfg)
    return dict(
        models=m,
        targets=unique,
        aliases=aliases,
        cards=cards,
        plans=plans,
        tape=t,
        shock=shock,
        cfg=cfg,
        unavailable=unavailable,
    )
