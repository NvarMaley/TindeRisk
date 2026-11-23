"""Apply a confirmed client's hard limits to a dated universe before solving."""
from dataclasses import replace

from .mandate import account_gate


def solve_account(snapshot, register, as_of, *, model=None, model_date=None, exposure_limits=None):
    """A limit maps (card, scope) to (coefficients by stable instrument ID, remaining pocket cap).

    Caps are fractions of the investable pocket after existing outside exposures.
    model.current contains current positions inside that pocket in the same units.
    """
    gate = account_gate(snapshot, register, as_of)
    if not gate["ids"]:
        return gate
    if model is None or model_date != as_of or set(model.names) != set(gate["ids"]):
        return gate | {"status": "market entry to be reconciled with the dated register"}
    from .engine import Frontier
    import numpy as np

    limits = exposure_limits or {}
    groups = dict(model.groups)
    for check in snapshot["portrait"]["mandatory_checks"]:
        key = (check["card"], check["scope"])
        if key not in limits:
            return gate | {"status": "mandatory exposure to be documented", "rule": list(key)}
        by_asset, cap = limits[key]
        values = np.array([by_asset.get(asset, np.nan) for asset in model.names], dtype=float)
        if not np.isfinite(values).all() or cap is None or not np.isfinite(cap):
            return gate | {"status": "incomplete mandatory exposure", "rule": list(key)}
        groups["mandate · " + " · ".join(key)] = (values, cap)
    constrained = replace(model, groups=groups)
    engine = Frontier(constrained)
    if gate["mode"] == "minimum":
        solution = engine.solve(minimum=True)
    else:
        solution = engine.solve(low=gate["low"], high=gate["high"])
    return gate | {"status": solution["status"], "continuous": solution}
