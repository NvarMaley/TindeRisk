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
    if not validated["demo_eligible"] or mandate["as_of"]<"2026-11-25" or data["version"]!=VERSION:
        raise ValueError("Historical USD mandate unavailable")
    profile=ClientProfile(mandate["capital"],validated["horizon_years"],validated["effective_stress_limit"])
    names=data["names"]
    allocation=blend(root,profile,names,data["budgets"],False)
    rows,split,reference=catalog(root)
    frozen=json.loads((Path(root)/"data/processed/walk_forward"/f"{REFERENCE_RUN}.json").read_text())
    cash=np.asarray(frozen["benchmarks"]["cash"]["returns"],float)
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
    return {"status":"experimental","version":"match-goals-v1","reference_run":REFERENCE_RUN,
            "paths":1000,"training_months":split,"horizon_months":months,
            "matched":matched,"reference":baseline,
            "warning":"Conditional block bootstrap on development data including modeled monthly sleeve transfer fees; actual distributions, contractual hedges and liability DV01 are not modeled."}
