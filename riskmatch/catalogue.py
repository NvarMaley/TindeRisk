"""Prepare the dated CHF frontier and historical replay offline."""
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

ASSETS = ["SPY","IEF","GLD","Cash CHF"]
DECISION = pd.Timestamp("2013-12-31")
ENTRY = pd.Timestamp("2014-01-02")
FEE = .002  # Titles + change based on the amount of ETF traded


def build(root):
    prices = pd.read_csv(root/"data/raw/etf_prices_adjusted.csv",index_col=0,parse_dates=True)[ASSETS[:3]]
    fx = pd.read_csv(root/"data/raw/public_phase2/DEXSZUS.csv",index_col=0,parse_dates=True).iloc[:,0]
    levels = prices.mul(fx.reindex(prices.index),axis=0)
    levels["Cash CHF"] = 1.
    # Even with a conservative timeframe and session window, as used in the CHF pilot.
    window = levels.pct_change(fill_method=None).loc[:DECISION-pd.Timedelta(days=10)].tail(756).dropna()
    assert len(window) >= .9*756
    mu, cov = window.mean().to_numpy()*252, window.cov().to_numpy()*252
    w = cp.Variable(4)
    catalogue = []
    for cap in np.arange(0, .181, .005):
        if cap == 0:
            weights = np.array([0.,0.,0.,1.])
        else:
            problem = cp.Problem(cp.Maximize(mu@w-FEE*cp.sum(w[:3])),
                                 [cp.sum(w)==1,w>=0,cp.quad_form(w,cov)<=cap**2])
            problem.solve(solver="CLARABEL")
            if problem.status != cp.OPTIMAL:
                raise ValueError("Frontier optimization failed")
            weights = np.maximum(w.value,0)
            weights /= weights.sum()
        risk = np.sqrt(weights@cov@weights)
        assert risk <= cap+1e-6
        if catalogue and np.max(abs(weights-catalogue[-1]["weights"]))<.0001:
            continue
        catalogue.append(dict(weights=weights.tolist(), risk=risk,
                              net=(1+mu@weights)/(1+FEE*sum(weights[:3]))-1))
    valid = levels.loc[ENTRY:"2015"].dropna()
    replay = []
    for month in range(24):
        row = valid.loc[:ENTRY+pd.DateOffset(months=month)].iloc[-1]
        replay.append(dict(month=month,date=row.name.date().isoformat(),
                           relative=(row/valid.loc[ENTRY]).tolist()))
    return dict(version="chf-2013-v1",decision=str(DECISION.date()),entry=str(ENTRY.date()),
                estimated_through=str(window.index[-1].date()),observations=len(window),
                assets=ASSETS,fee=FEE,cov=cov.tolist(),frontier=catalogue,replay=replay)


def save(root):
    data = build(root)
    path = root/"data/demo/chf_walkthrough.json"
    path.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)+"\n")
    return data


if __name__=="__main__":
    save(Path(__file__).resolve().parents[1])
