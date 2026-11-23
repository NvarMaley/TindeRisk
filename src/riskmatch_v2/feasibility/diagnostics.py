"""Independent checks on real prices and a robust research alternative."""
from dataclasses import replace
from itertools import combinations
import numpy as np
import pandas as pd
from .inputs import estimate
from .engine import Frontier


def equal_cap_vertices(p):
    """Exact vertices for the declared equal-cap, homogeneous-cost, initially cash mandate."""
    if (np.any(p.current) or np.any(p.lo) or p.invested_min or not np.all(p.hi==p.hi[0])
        or not np.all(p.fees==p.fees[0]) or any(not np.all(a==1) for a,_ in p.groups.values())):
        raise ValueError("This certificate requires a mandate with uniform ceilings")
    n=len(p.names)
    cap=p.hi[0]
    budget=min(p.invested_max,1/(1+p.fees[0]),*(v for _,v in p.groups.values()),1.)
    yield np.zeros(n)
    if cap<=0:
        return
    for k in range(min(n,int(budget/cap))+1):
        for group in combinations(range(n),k):
            w=np.zeros(n)
            w[list(group)]=cap
            if k:
                yield w.copy()
            rem=budget-k*cap
            if 1e-12<rem<cap-1e-12:
                for i in range(n):
                    if i not in group:
                        v=w.copy()
                        v[i]=rem
                        yield v


def crosschecks(p, etf, folder, cfg):
    count=0
    highest=None
    for v in equal_cap_vertices(p):
        c=p.evaluate(v)
        if not c["valid"]:
            raise ValueError("Invalid summit")
        if highest is None or c["risk"]>highest["risk"]:
            highest=c
        count+=1
    # Exhaustive independent comparison on a 0.1 percentage point two-ETF grid.
    names=["SPY","IEF"]
    mu,r=estimate(etf[names].tail(504))
    root=r.toarray()
    from .study import market
    pair=market(names,mu,r,cfg)
    reference=Frontier(pair).solve(high=.12)
    mesh=np.arange(601)/1000
    x,y=np.meshgrid(mesh,mesh)
    w=np.array([x.ravel(),y.ravel()])
    risk=np.linalg.norm(root@w,axis=0)
    fee=.001*w.sum(axis=0)
    good=(w.sum(axis=0)<=.9+1e-12)&(w.sum(axis=0)+fee<=1)&(risk<=.12)
    grid=float((mu@w-fee)[good].max())
    gap=reference["candidate"]["net"]-grid
    if not -1e-6<=gap<=.0001:
        raise ValueError("Disagreement with independent grid")
    stable=pd.read_parquet(folder/"stability_weights.parquet")
    models=[]
    data=etf.tail(504)
    rng=np.random.default_rng(cfg["seed"])
    options=[(data,"LedoitWolf",.5,.001),(data,"LedoitWolf",.75,.001),(etf.tail(756),"LedoitWolf",.5,.001),
             (data,"empirical",.5,.001),(data,"factor",.5,.001),(data,"LedoitWolf",.5,.0025)]
    for _ in range(10):
        block=np.concatenate([np.arange(i,i+21) for i in rng.integers(0,len(data)-20,24)])
        options.append((data.iloc[block],"LedoitWolf",.5,.001))
    for window,method,shrink,fee in options:
        m,r=estimate(window,method,shrink)
        models.append(replace(p,mu=m,root=r,fees=np.full(len(m),fee)))
    choices={}
    for name,w in stable.items():
        w=w.to_numpy()
        worst_risk=max(np.linalg.norm(m.root@w) for m in models)
        scaled=w*min(1,.12/worst_risk) if worst_risk else w
        checked=[m.evaluate(scaled,high=.12) for m in models]
        if all(c["valid"] for c in checked):
            choices[name]=(min(c["net"] for c in checked),scaled,max(c["risk"] for c in checked))
    winner=max(choices,key=lambda k:choices[k][0])
    worst,weights,risk=choices[winner]
    # Test the ordering of fixed portfolios under different models.
    contenders=["reference","756 sessions","lower averages"]
    rankings=[]
    for m in models:
        rankings.append(sorted(contenders,key=lambda k:m.evaluate(stable[k].to_numpy())["net"],reverse=True))
    from ..benchmark import write_json
    write_json(folder/"certificats.json",dict(names=p.names,max_risk=highest,robust_weights=weights.tolist(),rankings=rankings))
    return dict(vertices=count,max_risk=highest["risk"],max_risk_net=highest["net"],grid_best=grid,grid_gap=gap,
                robust_source=winner,robust_worst_net=worst,robust_worst_risk=risk,robust_models=len(models),
                rank_changes=sum(r!=rankings[0] for r in rankings),rank_runs=len(rankings))
