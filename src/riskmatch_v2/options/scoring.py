"""Common, versioned scoring grid for portfolios with the same mandate."""

import json
import math
from pathlib import Path

from ..forecast.registry import resolve

FAMILIES = ("macro", "market", "quantitatif", "sentiment")


def scale(x, edges):
    a, b = edges
    return 100 * min(1.0, max(0.0, (x - a) / (b - a)))


def signal_score(signals, registry, day, scope):
    if not signals:
        return None
    weights = resolve(registry, day, scope, "CHF return", "12 months")
    if set(weights) != set(FAMILIES):
        return None
    values = []
    for family in FAMILIES:
        s = signals.get(family, {})
        if (
            s.get("validated") is not True
            or s.get("target") != "CHF return"
            or s.get("months") != 12
            or not s.get("evidence")
            or not isinstance(s.get("value"), (int, float))
            or not 0 <= s["value"] <= 100
        ):
            return None
        # A portfolio card cannot substitute a new value or version for the approved score.
        entry = max(
            (
                r
                for r in registry
                if r["scope"] == scope
                and r["target"] == "CHF return"
                and r["horizon"] == "12 months"
                and r["name"] == family
                and r["issued"] <= day
            ),
            key=lambda r: (r["issued"], r["version"]),
        )
        if entry.get("score_100") != s["value"] or entry["version"] != s.get("version"):
            return None
        values.append(weights[family] * s["value"])
    return sum(values)


def rank(cards, priorities, cfg, *, research=False, goal=None, registry=None):
    if (
        set(priorities) != set(cfg["profiles"]["Goal"])
        or any(not math.isfinite(w) or w < 0 for w in priorities.values())
        or abs(sum(priorities.values()) - 100) > 1e-8
    ):
        raise ValueError("Invalid weighting")
    goal = cfg["goal"] if goal is None else goal
    if not math.isfinite(goal) or goal <= 0:
        raise ValueError("Positive performance target required by this grid")
    scale_edges = cfg["scales"]
    excluded = {}
    if registry is None:
        path = Path("reports/12-forecasts/registry.json")
        registry = json.loads(path.read_text()) if path.is_file() else []
    raw = {}
    for name, c in cards.items():
        if not c["valid"] or (not research and not c.get("tradable", False)):
            excluded[name] = "outside mandate or unverified negotiability"
            continue
        fields = ["net", "loss", "hhi", "fee", "cagr", "drawdown"]
        if any(c.get(k) is None or not math.isfinite(c[k]) for k in fields):
            excluded[name] = "missing indispensable measure"
            continue
        raw[name] = dict(
            goal=scale(c["net"], [0, 2 * goal]),
            history=0.75 * scale(c["cagr"], scale_edges["history"])
            + 0.25 * scale(-c["drawdown"], [0.40, 0]),
            stress=scale(max(0.0, c["loss"]), scale_edges["stress"]),
            spread=scale(c["hhi"], scale_edges["spread"]),
            cost=scale(c["fee"], scale_edges["cost"]),
            forecast=signal_score(c.get("signals"), registry, cfg["market"], name),
        )
    full = bool(raw) and all(v["forecast"] is not None for v in raw.values())
    active = [k for k in priorities if k != "forecast" or full]
    coverage = sum(priorities[k] for k in active)
    if not coverage:
        return dict(
            version=cfg["version"],
            coverage=0,
            rows={},
            excluded={
                **excluded,
                **dict.fromkeys(raw, "no weighted criteria available"),
            },
        )
    weights = {k: priorities[k] / coverage for k in active}
    rows = {}
    for name, v in raw.items():
        contributions = {k: v[k] * weights[k] for k in active}
        rows[name] = dict(
            subscores={k: v[k] for k in active},
            contributions=contributions,
            total=sum(contributions.values()),
        )
    best = None
    group = 0
    for name in sorted(rows, key=lambda k: -rows[k]["total"]):
        score = rows[name]["total"]
        if best is None or best - score > cfg["tie_points"]:
            group += 1
            best = score
        rows[name]["group"] = group
    return dict(
        version=cfg["version"],
        mode="historical research" if research else "account",
        grid="Complete" if full else "historical history without forecasts",
        coverage=coverage,
        weights=weights,
        rows=rows,
        excluded=excluded,
    )
