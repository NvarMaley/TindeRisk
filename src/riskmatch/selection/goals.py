"""Conditional financial-objective assessment for a confirmed historical Match."""
import json
from pathlib import Path
from datetime import date
import numpy as np
from riskmatch.analytics.objectives import evaluate, bootstrap_indices
from riskmatch.profiling.mandate import validate_mandate, add_month
from riskmatch.prototype import ClientProfile
from riskmatch.historical_matches import catalog, blend, VERSION
from riskmatch.matching import REFERENCE_RUN


def assess(root, data):
    mandate=data["mandate"]
    validated=validate_mandate(mandate)
    names=data["names"]
    from riskmatch import personalized_matches as pm
    if pm.is_version(data["version"]):
        context=pm.resolve(root,mandate,data["version"])
        allocation=pm.blend(root,mandate,data["version"],names,data["budgets"],False)
        rows,split,reference,cash=(context[k] for k in ("rows","split","reference","cash"))
        reference_run=context["version"]
    else:
        if not validated["demo_eligible"] or mandate["as_of"]<"2026-11-25" or data["version"]!=VERSION:
            raise ValueError("Historical USD mandate unavailable")
        profile=ClientProfile(mandate["capital"],validated["horizon_years"],validated["effective_stress_limit"])
        allocation=blend(root,profile,names,data["budgets"],False)
        rows,split,reference=catalog(root)
        frozen=json.loads((Path(root)/"data/processed/walk_forward"/f"{REFERENCE_RUN}.json").read_text())
        cash=np.asarray(frozen["benchmarks"]["cash"]["returns"],float)
        reference_run=REFERENCE_RUN
    from riskmatch.selection.sleeve_ledger import rebalance_paths
    components,_,_=rebalance_paths(np.column_stack([rows[k][2][:split] for k in names]),list(allocation["budgets"].values()))
    combined=components.sum(axis=1)
    start=date.fromisoformat(validated["as_of"]);end=date.fromisoformat(validated["horizon_date"])
    months=1
    while add_month(start,months)<end:months+=1
    if months>600:
        raise ValueError("Research scenario horizon exceeds 50 years")
    indices=bootstrap_indices(split,months,paths=1000,block=6,seed=25)
    matched=evaluate(mandate,combined[:split][indices],cash[:split][indices],report=validated)
    baseline=evaluate(mandate,reference[:split][indices],cash[:split][indices],report=validated)
    return {"status":"experimental","version":"match-goals-v1","reference_run":reference_run,
            "paths":1000,"benchmark":context["benchmark"] if pm.is_version(data["version"]) else "60/40", "training_months":split,"horizon_months":months,
            "matched":matched,"reference":baseline,
            "warning":"Conditional block bootstrap on development data including modeled monthly sleeve transfer fees; actual distributions, contractual hedges and liability DV01 are not modeled."}


def compare_allocations(root, data):
    """Compare feasible budgets using identical goal paths, including two-way mixes."""
    from riskmatch import personalized_matches as pm
    mandate, version, names = data["mandate"], data["version"], data["names"]
    ctx = pm.resolve(root, mandate, version)
    manual = pm.blend(root, mandate, version, names, data["budgets"], False)
    minimum = pm.blend(root, mandate, version, names, None, True)
    proposed = np.array(list(manual["budgets"].values()))
    safer = np.array(list(minimum["budgets"].values()))
    priority = max(g["priority"] for g in mandate["goals"])
    def evaluate(budgets):
        request = dict(data, budgets=list(budgets))
        projection = assess(root, request)["matched"]["goals"]
        selected = [g for g in projection if g["priority"] == priority]
        lam = ctx["cards"][0]["risk_aversion_parameter"]
        values = [pm.objective_fit(g, lam) for g in selected]
        measured = [v for v in values if v is not None]
        return {"score": float(np.mean(measured)) if measured else None,
                "goals": [{k: g[k] for k in ("objective_id","probability","expected_deficit")}
                          for g in selected]}
    options = {}
    def add(budgets):
        key = tuple(np.round(budgets, 10))
        if key not in options:
            options[key] = (budgets, evaluate(budgets))
        return options[key]
    original = add(proposed)
    conservative = add(safer)
    add(np.ones(len(names))/len(names))
    # Test each retained strategy alone, then mix the best single with the
    # manual and minimum-variance budgets on a deterministic quarter grid.
    singles = [add(b) for b in np.eye(len(names))]
    def rank(option):
        score = option[1]["score"]
        return -1 if score is None else score
    best_single = max(singles, key=rank)[0]
    for fraction in (.25, .5, .75):
        for base in (proposed, safer):
            add(base*(1-fraction)+best_single*fraction)
    best = max(options.values(), key=rank)
    if best[1]["score"] is None:
        raise ValueError("Priority objective cannot be measured for this mandate")
    result = pm.blend(root, mandate, version, names, best[0], False)
    result["comparison"] = {}
    for label,(budgets,summary) in (("manual",original),("minimum_variance",conservative),("goal",best)):
        candidate = pm.blend(root, mandate, version, names, budgets, False)
        result["comparison"][label] = dict(summary, budgets=candidate["budgets"],
                                            stress_loss=candidate["stress_loss"])
    result["tested_budgets"] = len(options)
    return result
