"""Chapter 26 comparison on the exact frozen chapter 25 sleeve paths."""
import json
from pathlib import Path
import numpy as np
from riskmatch.dynamic.policies import VERSION, POLICIES, simulate
from riskmatch.historical_matches import catalog, blend, VERSION as MATCH_VERSION
from riskmatch.matching import REFERENCE_RUN
from riskmatch.profiling.mandate import validate_mandate, SCHEMA_VERSION
from riskmatch.prototype import ClientProfile


def report(root, data):
    mandate=data["mandate"]
    from riskmatch import personalized_matches as pm
    personalized=pm.is_version(data.get("version"))
    if personalized:
        if mandate.get("schema_version")!=SCHEMA_VERSION:
            raise ValueError("Personalized mandate required")
        if ("cash" not in mandate["constraints"]["allowed_assets"] or
                pm.hard_limit(mandate,"max_asset_weight",1.)<1 or
                pm.hard_limit(mandate,"volatility",1.)<1):
            raise ValueError("Dynamic cash overlay cannot certify the specified cash, asset-weight or volatility restriction")
    if mandate.get("schema_version")==SCHEMA_VERSION:
        m=validate_mandate(mandate)
        if not m["personalized_eligible" if personalized else "demo_eligible"] or mandate["as_of"]<"2026-11-25":
            raise ValueError("Mandate not supported by historical USD experiment")
        if mandate["dated_flows"]:
            raise ValueError("Dated flows require a separate liability ledger")
        profile=ClientProfile(mandate["capital"],m["horizon_years"],m["effective_stress_limit"])
    else:
        profile=ClientProfile(**mandate)
    if not personalized and data["version"]!=MATCH_VERSION:
        raise ValueError("Historical Matches required")
    names=data["names"]
    if personalized:
        context=pm.resolve(root,mandate,data["version"])
        selected=pm.blend(root,mandate,data["version"],names,data["budgets"],False)
        rows,split,cash,dates=(context[k] for k in ("rows","split","cash","dates"))
        reference_run=context["version"]
    else:
        selected=blend(root,profile,names,data["budgets"],False)
        rows,split,_=catalog(root)
        frozen=json.loads((Path(root)/"data/processed/walk_forward"/f"{REFERENCE_RUN}.json").read_text())
        cash=frozen["benchmarks"]["cash"]["returns"]
        dates=frozen["dates"]
        reference_run=REFERENCE_RUN
    x=np.column_stack([rows[k][2] for k in names])
    weights=list(selected["budgets"].values())
    # Conservative envelope protects against changes in sleeve allocations.
    worst=max(max(0.,-min(rows[k][1].values())) for k in names)
    options=dict(cost_bps=float(data.get("cost_bps",10)),frequency=data.get("frequency",1),
                 contribution=float(mandate.get("contribution_monthly",0)),
                 withdrawal=float(mandate.get("withdrawal_monthly",0)))
    results={p:simulate(x,cash,dates,split,profile.capital,p,weights,
                        profile.max_stress_loss,worst,**options) for p in ("static","drift",*POLICIES)}
    sensitivity={}
    for label,changes in (("double_fees",{"cost_bps":min(100.,2*options["cost_bps"])}),
                          ("quarterly",{"frequency":3})):
        sensitivity[label]={}
        for p in ("static",*POLICIES):
            trial=simulate(x,cash,dates,split,profile.capital,p,weights,
                           profile.max_stress_loss,worst,**(options|changes))
            sensitivity[label][p]={k:v for k,v in trial.items() if k in ("status","fees","cagr","volatility","annual_turnover")}
    return dict(status="experimental",version=VERSION,match_version=data["version"],
                dates=dates[split:],names=names,policies=results,
                selection={k:selected[k] for k in ("weights","budgets","scenarios","metrics","stress_loss")},
                settings={**options,"capital":profile.capital,"stress_limit":profile.max_stress_loss},
                reference_run=reference_run,
                sensitivity=sensitivity,
                assumptions="Historical USD sleeve returns; one-month signal lag; additional sleeve transfer fees; modeled cash reserve; no real orders. Monthly recurring flows replayed; no dated liabilities or current execution data.")
