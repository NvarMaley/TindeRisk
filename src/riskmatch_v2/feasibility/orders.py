"""Lot conversion and independent post-trade checks for a funded CHF pocket."""
from itertools import product
from math import prod
import numpy as np


def orders(problem, target, pocket, prices, fx, lots, existing, *, low=0., high=None, max_trials=25000):
    arrays=[np.asarray(a,dtype=float) for a in (prices,fx,lots,existing)]
    prices,fx,lots,existing=arrays
    if not np.isfinite(pocket) or pocket<=0 or any(a.shape!=problem.mu.shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError("Incomplete budget or quotations")
    if any(np.any(a<=0) for a in (prices,fx,lots)) or (existing<0).any():
        raise ValueError("Invalid price, change, lot or position")
    unit=prices*fx*lots/pocket
    initial=existing*prices*fx/pocket
    if not np.allclose(initial,problem.current,rtol=0,atol=1e-8):
        raise ValueError("The initial units do not match the portfolio")
    # A trade must be a lot multiple even if the existing position is an odd lot.
    a=np.ceil((problem.lo-initial-1e-12)/unit).astype(int)
    b=np.floor((problem.hi-initial+1e-12)/unit).astype(int)
    goal=(np.asarray(target)-initial)/unit
    exhaustive=prod(max(0,int(y-x+1)) for x,y in zip(a,b))<=max_trials
    if exhaustive:
        grids=[range(x,y+1) for x,y in zip(a,b)]
    else:
        grids=[sorted(set(int(np.clip(z,x,y)) for z in (round(t),np.floor(t),np.ceil(t),0)),
                      key=lambda z:abs(z-t)) if y>=x else [] for x,y,t in zip(a,b,goal)]
    best=None
    distance=np.inf
    count=0
    for trades in product(*grids):
        if count>=max_trials:
            break
        count+=1
        w=initial+unit*np.array(trades)
        c=problem.evaluate(w,low,high)
        d=np.linalg.norm(np.asarray(target)-w)
        if c["valid"] and c["funding"]>=-1e-10 and d<distance:
            distance=d
            best=dict(candidate=c,units=(existing+np.array(trades)*lots).tolist(),
                      trade_units=(np.array(trades)*lots).tolist(),fee_chf=c["fee"]*pocket,
                      cash_chf=c["cash"]*pocket,distance=float(d))
    return dict(status="checked batches" if best else "impossible in batches" if exhaustive else "inconclusive",
                examined=count,exhaustive=exhaustive,order=best)
