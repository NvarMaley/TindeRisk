"""Scope- and version-aware admission of forecasts into research allocation."""

import math
from datetime import date


def resolve(registry, asof, scope, target, horizon):
    cutoff = date.fromisoformat(asof)
    latest = {}
    for row in registry:
        if (row["scope"], row["target"], row["horizon"]) != (scope, target, horizon):
            continue
        issued = date.fromisoformat(row["issued"])
        if issued <= cutoff:
            key = (issued, row["version"])
            if row["name"] not in latest or key > latest[row["name"]][0]:
                latest[row["name"]] = (key, row)
    allowed = {}
    for name, (_, row) in latest.items():
        if (
            row["status"] == "approved"
            and date.fromisoformat(row["expires"]) >= cutoff
            and math.isfinite(row["weight"])
            and row["weight"] > 0
        ):
            allowed[name] = row["weight"]
    total = sum(allowed.values())
    return {k: v / total for k, v in allowed.items()}


def opinion(weights, values, reference):
    if not weights or any(not math.isfinite(values.get(k, math.nan)) for k in weights):
        return reference, {}
    parts = {key: w * values[key] for key, w in weights.items()}
    return sum(parts.values()), parts


def controlled_estimate(registry, asof, scope, target, horizon, signals, reference):
    return opinion(resolve(registry, asof, scope, target, horizon), signals, reference)


def controls():
    row = {
        "scope": "SPY in CHF",
        "target": "return",
        "horizon": 21,
        "name": "a",
        "issued": "2026-09-01",
        "expires": "2026-10-31",
        "version": 1,
        "weight": 1.0,
        "status": "approved",
    }
    entries = [
        row,
        dict(row, name="rejected", status="rejected"),
        dict(row, name="stale", expires="2026-09-02"),
        dict(row, issued="2026-10-02", version=2, status="withdrawn"),
    ]
    values = {"a": 0.02, "rejected": 3.0, "stale": 2.0}

    def call(when):
        return controlled_estimate(
            entries, when, row["scope"], "return", 21, values, 0.005
        )

    old = call("2026-10-01")
    withdrawn = call("2026-10-03")
    opposition = opinion({"a": 0.5, "b": 0.5}, {"a": 0.03, "b": -0.02}, 0.0)
    missing = opinion({"a": 0.5, "b": 0.5}, {"a": 0.03}, 0.005)
    assert (
        old == (0.02, {"a": 0.02})
        and withdrawn == (0.005, {})
        and missing == (0.005, {})
    )
    return {
        "previous": old,
        "withdrawn": withdrawn,
        "opposed": opposition,
        "missing": missing,
        "extreme_rejected_value": 3.0,
        "expired_value": 2.0,
    }
