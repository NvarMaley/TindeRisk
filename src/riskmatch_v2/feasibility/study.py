"""Reproduce section 5. Publish aggregates and retain all individual inputs locally."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from statistics import median
from threading import Event, Thread
from time import monotonic
import json
import os

import numpy as np
import pandas as pd
from scipy import sparse
import psutil

from ..benchmark import write_json
from .engine import Frontier, Problem
from .inputs import CFG, LOCAL, REPORT, daily_inputs, estimate, factors, signature
from .orders import orders
from .diagnostics import crosschecks


def market(names,mu,root,cfg):
    n=len(names)
    return Problem(tuple(names),mu,root,np.zeros(n),np.full(n,cfg["maximum_par_titre"]),np.zeros(n),
                   np.full(n,sum(cfg["frais_pb"].values())/10000),
                   {"devise_USD":(np.ones(n),cfg["maximum_investi"])},
                   invested_max=cfg["maximum_investi"],years=cfg["horizon_ans"])


def compact(r):
    c=r["candidate"] or {}
    return dict(status=r["status"],proof=r["proof"],risk=c.get("risk"),net=c.get("net"),
                cash=c.get("cash"),fee=c.get("fee"),turnover=c.get("turnover"),residual=c.get("residual"),
                gap=r["gap"],upper_net=r["upper_net"],max_risk_bound=r["max_risk_bound"],
                nodes=len(r["log"]),seconds=r["seconds"],active=c.get("active",[]))


def cache_key(p, request, snapshot):
    h=sha256(snapshot.encode())
    for x in (p.mu,p.lo,p.hi,p.current,p.fees,p.root.data,p.root.indices,p.root.indptr):
        h.update(x.tobytes())
    h.update(json.dumps([p.names,p.root.shape,p.invested_min,p.invested_max,p.years,p.prefund,
                        {k:[a.tolist(),cap] for k,(a,cap) in p.groups.items()},request],sort_keys=True).encode())
    return h.hexdigest()


def cached(p, request, folder, snapshot):
    key=cache_key(p,request,snapshot)
    out=folder/"solutions"/(key+".json")
    if out.is_file():
        return json.loads(out.read_bytes()),True
    r=Frontier(p).solve(**request)
    write_json(out,r)
    return r,False


def timing(n, fn):
    from psutil import Process
    process=Process(os.getpid())
    times,states,gaps,peaks=[],[],[],[]
    for _ in range(3):
        stop=Event()
        rss=[process.memory_info().rss]
        def sample():
            while not stop.wait(.01):
                rss.append(process.memory_info().rss)
        worker=Thread(target=sample)
        worker.start()
        start=monotonic()
        try:
            r=fn()
        finally:
            stop.set()
            worker.join()
        times.append(monotonic()-start)
        peaks.append(max(rss+[process.memory_info().rss])/2**20)
        states.append(r["status"])
        gaps.append(r.get("gap"))
    return dict(n=n,repetitions=3,median=median(times),worst=max(times),peak_rss_mib=max(peaks),
                statuses=states,gaps=gaps)


def held_out(etf,cfg):
    results=[]
    for end in [0,63,126]:
        split=len(etf)-end-63
        future=etf.iloc[split:split+63].dropna()
        for window in cfg["windows"]:
            train=etf.iloc[split-window:split]
            for method in ("empirical","LedoitWolf","factor"):
                _,root=estimate(train,method)
                w=np.full(etf.shape[1],1/etf.shape[1])
                pred=float(np.linalg.norm(root@w))
                realized=float((future@w).std()*np.sqrt(252))
                results.append(dict(first=future.index[0],last=future.index[-1],method=method,
                                    window=window,n=len(future),train_common=len(train.dropna()),
                                    predicted=pred,realized=realized,error=pred-realized))
    return results


def stability(etf,p,cfg,folder):
    data=etf.tail(504)
    rng=np.random.default_rng(cfg["seed"])
    variants={"reference":p}
    def fit(panel,method="LedoitWolf",shrink=.5):
        mu,root=estimate(panel,method,shrink)
        return replace(p,mu=mu,root=root)
    variants.update({"lower averages":fit(data,shrink=.75),"756 sessions":fit(etf.tail(756)),
                     "empirical":fit(data,"empirical"),"factor":fit(data,"factor"),
                     "cost 25 pb":replace(p,fees=p.fees*2.5)})
    for i in range(10):
        starts=rng.integers(0,len(data)-21+1,24)
        block=np.concatenate([np.arange(j,j+21) for j in starts])
        variants[f"blocs {i+1}"]=fit(data.iloc[block])
    rows=[]
    weights={}
    for name,model in variants.items():
        solved=Frontier(model).solve(high=.12)
        c=solved["candidate"]
        if c is None:
            raise ValueError("Unverified variant: "+name)
        w=np.array(c["weights"])
        weights[name]=w
        base=weights["reference"]
        rows.append(dict(name=name,status=solved["status"],net=c["net"],risk=c["risk"],turnover=c["turnover"],
                         weight_distance=float(abs(w-base).sum()/2),
                         largest_weight_shift=float(abs(w-base).max()), spread_weights=float(w.max()-w.min()),
                         rank_changed=bool(model.mu.argmax()!=p.mu.argmax()),
                         leader_changed=bool(w.argmax()!=base.argmax()),reference_risk=p.evaluate(w)["risk"]))
    pd.DataFrame(weights,index=p.names).to_parquet(folder/"stability_weights.parquet")
    return rows


def oracle_cases():
    names=("defensive","risky")
    p=Problem(names,np.array([.06,.02]),np.array([[.02,.20]]),np.zeros(2),np.ones(2),
              np.array([1.,0.]),np.zeros(2),{},invested_min=1.)
    # Linear positive exposure in this example. The unique best target has risky weight 4/9.
    e=Frontier(p)
    all_cases={}
    for name,args in {"under ceiling":dict(high=.14),"binding lower volatility bound":dict(low=.10,high=.14,nodes=128,seconds=8),
                      "interruption":dict(low=.10,high=.14,nodes=0),"impossible":dict(low=.35,high=.40)}.items():
        all_cases[name]=e.solve(**args)
    solution=all_cases["binding lower volatility bound"]
    assert solution["status"]=="optimal" and abs(solution["candidate"]["net"]-(.06-.04*4/9))<=.0001
    assert all_cases["interruption"]["candidate"] and all_cases["interruption"]["status"]=="candidate"
    return {k:compact(v) for k,v in all_cases.items()},all_cases


def examples_lots():
    p=Problem(("Share A","part B"),np.array([.04,.03]),np.diag([.12,.06]),np.zeros(2),np.full(2,.7),
              np.zeros(2),np.full(2,.001),{"secteur_A":(np.array([1,0]),.50)}, invested_max=.9)
    small=orders(p,[.50,.40],1000,[88,61],[.9,.9],[1,1],[0,0],high=.12)
    debt=Problem(("fictitious obligation",),np.array([.03]),np.array([[.04]]),np.array([.4]),np.array([.9]),
                 np.zeros(1),np.array([.001]),{})
    bond=orders(debt,[.60],500,[100],[.9],[10],[0])
    alternative=orders(replace(debt,lo=np.zeros(1)),[0],500,[100],[.9],[10],[0])
    return {"small investment sleeve":small,"Bond lot":bond,"Cash if minimum raised":alternative}


def main():
    cfg=json.loads(CFG.read_bytes())
    key,versions=signature(cfg)
    daily,wide,cat=daily_inputs(cfg,key)
    etf=daily.loc[:cfg["date_cours"]]
    engine_hash=sha256(b"".join(Path(__file__).with_name(f).read_bytes() for f in
                                ["study.py","engine.py","orders.py","mandate.py","diagnostics.py"])).hexdigest()[:16]
    snapshot=key+"-"+engine_hash
    folder=LOCAL/cfg["version"]/snapshot
    folder.mkdir(parents=True,exist_ok=True)
    a=etf.tail(504)
    mu,root=estimate(a)
    p=market(etf.columns,mu,root,cfg)
    np.savez_compressed(folder/"etf_moments.npz",ids=np.array(p.names),mu=mu,root=root.toarray())
    a.to_parquet(folder/"etf_sessions.parquet")
    e=Frontier(p)
    raw={}
    for target in [0,.02,.04,.06,.08,.10,.12,.14,.16,.18,.20,.24,.35,.40,1.]:
        raw[f"cap {target:g}"]=e.solve(high=target)
    raw["minimum"]=e.solve(minimum=True)
    for low,high in [(.34,.36),(.38,.42),(.99,1.01)]:
        raw[f"band {low:g}–{high:g}"]=e.solve(low=low,high=high)
    base=raw["cap 0.12"]["candidate"]
    if not base:
        raise ValueError("Reference case without tell-tale")
    hi=p.hi.copy()
    excluded=np.argsort(base["weights"])[-2:]
    hi[excluded]=0
    raw["two exclusions"]=Frontier(replace(p,hi=hi)).solve(high=.12)
    write_json(folder/"etf_solutions.json",dict(names=p.names,results=raw))
    o,full_oracle=oracle_cases()
    write_json(folder/"oracle.json",full_oracle)
    held=held_out(etf,cfg)
    var=stability(etf,p,cfg,folder)
    # All dated active PERMNOs are considered, including unavailable/short histories.
    names,wide_mu,wide_root,counts=factors(wide,cfg["factors"],cfg["min_obs_facteurs"])
    wp=market(names,.5*wide_mu+.5*np.median(wide_mu),wide_root,cfg)
    sparse.save_npz(folder/"factor_root.npz",wide_root)
    np.save(folder/"factor_mu.npy",wp.mu)
    write_json(folder/"factor_universe.json",dict(submitted=names,observations=counts,missing=sorted(set(wide)-set(names))))
    ex=Frontier(wp)
    broad=ex.solve(high=.12)
    write_json(folder/"factor_solution.json",broad)
    # Compare the factor risk on precisely the same common ETF history.
    sub=[names.index(s) for s in etf.columns]
    w=np.ones(len(sub))/len(sub)
    empirical=np.sqrt(252)*float((wide[list(etf.columns)].dropna()@w).std())
    common_factor=float(np.linalg.norm(wide_root[:,sub]@w))
    decision=pd.read_parquet(cat/"decision.parquet")
    def screen():
        ids=decision.loc[decision.eligible,"id"].tolist()
        if ids:
            raise ValueError("New eligible register: value and verify these instruments")
        return dict(status="no eligible instrument",ids=ids)
    live=screen()
    write_json(folder/"admission.json",dict(date=decision.date.iloc[0],screened=decision.id.tolist(),**live))
    sample=wide[list(etf.columns)[:3]]
    sm,sr=estimate(sample)
    sp=market(sample.columns,sm,sr,cfg)
    performance=[timing(3,lambda:Frontier(sp).solve(high=.12)),timing(13,lambda:e.solve(high=.12)),
                 timing(len(names),lambda:ex.solve(high=.12)),timing(0,screen)]
    cached(p,{"high":.12},folder,snapshot)
    _,hit=cached(p,{"high":.12},folder,snapshot)
    _,other=cached(p,{"high":.121},folder,snapshot)
    assert hit and cache_key(p,{"high":.121},snapshot)!=cache_key(p,{"high":.12},snapshot)
    threshold=np.linalg.eigvalsh((root.T@root).toarray())
    report=dict(version=cfg["version"],snapshot=snapshot,versions=versions,date=etf.index[-1],
                lease=dict(pocket=cfg["solde_initial_chf"]-cfg["reserve_chf"],reserve=cfg["reserve_chf"]),
                fund_count=len(p.names),window=len(a),common=len(a.dropna()),min_eigen=float(threshold.min()),
                condition=float(threshold.max()/threshold.min()),cases={k:compact(v) for k,v in raw.items()},
                diagnostics=crosschecks(p,etf,folder,cfg),oracle=o,validation=held,stability=var,lots=examples_lots(),performance=performance,
                broad=dict(date=cfg["date_actions"],seen=wide.shape[1],modeled=len(names),
                           complete_rows=len(wide.dropna()),excluded=wide.shape[1]-len(names),
                           common_empirical=empirical,common_factor=common_factor,**compact(broad)),
                live=dict(date=decision.date.iloc[0],examined=len(decision),count=len(live["ids"]),status=live["status"]),
                cache=dict(same_hit=hit,changed_key=True),exclusions=[p.names[i] for i in excluded])
    write_json(REPORT/"resultats.json",report)
    print("Section 5",report["broad"]["modeled"],report["live"]["status"],folder,flush=True)


if __name__=="__main__":
    main()
