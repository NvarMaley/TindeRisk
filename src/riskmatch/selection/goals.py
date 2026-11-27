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
from riskmatch.backtesting.walk_forward import execute


def holdings_paths(history, weights, indices, cost=.001):
    """Replay each sampled month jointly, restoring the same asset weights."""
    x = np.asarray(history, float)
    w = np.asarray(weights, float)
    active = w > 0
    x, w = x[:, active], w[active]
    gross = 1. + x @ w
    # Preserve the cash slot so trading the cash component itself carries no fee.
    if active[-1]:
        target = w
        holdings = (1. + x) * w
    else:
        target = np.r_[w, 0.]
        holdings = np.column_stack([(1. + x) * w, np.zeros(len(x))])
    retained = np.ones(len(x))
    for i, position in enumerate(holdings):
        if gross[i] <= 0:
            raise ValueError("A historical scenario exhausts the projected portfolio")
        funded, _, _ = execute(position, target, cost)
        retained[i] = funded.sum() / gross[i]
    paths = gross[indices]
    paths[:, 1:] *= retained[indices[:, :-1]]
    return paths - 1.


def assess(root, data, *, include_path=True):
    mandate=data["mandate"]
    validated=validate_mandate(mandate)
    names=data["names"]
    discount = data.get("discount_rate")
    if discount is not None and (type(discount) not in (int,float)
                                 or not np.isfinite(discount) or not -.05 <= discount <= .30):
        raise ValueError("Invalid annual discount rate")
    from riskmatch import personalized_matches as pm
    if pm.is_version(data["version"]):
        context=pm.resolve(root,mandate,data["version"])
        allocation=pm.blend(root,mandate,data["version"],names,data["budgets"],False)
        _, _, history, rf, *_ = pm.market_data(Path(root).resolve())
        cash = rf[-pm.ESTIMATION_MONTHS:]
        history = np.column_stack([history[-pm.ESTIMATION_MONTHS:], cash])
        weights = np.array([allocation["weights"][label] for label in context["labels"]])
        split = len(cash)
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
    start=date.fromisoformat(validated["as_of"]);end=date.fromisoformat(validated["horizon_date"])
    months=1
    while add_month(start,months)<end:months+=1
    if months>600:
        raise ValueError("Research scenario horizon exceeds 50 years")
    indices=bootstrap_indices(split,months,paths=1000,block=6,seed=25)
    cash_paths = cash[:split][indices]
    if pm.is_version(data["version"]):
        combined_paths = holdings_paths(history, weights, indices)
        reference_paths = cash_paths
        benchmark = "USD cash"
        method = "joint_asset_blocks"
        warning = ("Joint six-month blocks from the frozen 60-month asset history; "
                   "fixed target weights, modeled monthly trading fees and no initial entry fee. "
                   "Cash is a comparison reference, even when the mandate rules it out.")
    else:
        from riskmatch.selection.sleeve_ledger import rebalance_paths
        components,_,_=rebalance_paths(np.column_stack([rows[k][2][:split] for k in names]),
                                       list(allocation["budgets"].values()))
        combined_paths = components.sum(axis=1)[indices]
        reference_paths = reference[:split][indices]
        benchmark = "60/40"
        method = "development_sleeve_blocks"
        warning = "Conditional six-month blocks from development sleeve returns with modeled transfer fees."
    cash_discount = float(np.expm1(12 * np.log1p(cash[:split]).mean()))
    applied_discount = discount if discount is not None else cash_discount
    matched=evaluate(mandate,combined_paths,cash_paths,report=validated,
                     include_wealth_path=include_path,discount_rate=applied_discount if include_path else None)
    baseline=evaluate(mandate,reference_paths,cash_paths,report=validated)
    return {"status":"experimental","version":"match-goals-v2","reference_run":reference_run,
            "paths":1000,"benchmark":benchmark,"method":method,"training_months":split,"horizon_months":months,
            "data_end": str(pm.DATA_END) if pm.is_version(data["version"]) else None,
            "discount_source":"historical_cash" if discount is None else "custom",
            "matched":matched,"reference":baseline,
            "warning":warning}


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
        projection = assess(root, request, include_path=False)["matched"]["goals"]
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
