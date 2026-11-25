"""Historical, paper-only chapter 25 strategy cards and blended return paths."""
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from threading import Lock

import numpy as np
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits

from riskmatch.matching import REFERENCE_RUN
from riskmatch.prototype import metrics

STRESS_RUN = '631f7088c157b5abe7301dc5751fa973e5e5042c571cb0f17a4fad25d9e18880'
VERSION = 'historical-usd-v1-' + REFERENCE_RUN + '-' + STRESS_RUN
PERIOD = '2022-03-31 – 2025-12-31 · USD'
COSTS = '10 bp · sleeve trades; 10 bp additional executed transfers in combined allocation'


_catalog_lock=Lock()


def catalog(root):
    # Concurrent clients share the first computation rather than fitting twice.
    with _catalog_lock:
        return _cached_catalog(Path(root).resolve())


@lru_cache(maxsize=2)
def _cached_catalog(root):
    from riskmatch.simulation.stress_report import (
        aligned, config, fit_models, load_signals, macro_signals, scenario_matrix, SIGNED,
    )
    folder = Path(root) / 'data/processed'
    try:
        walk = json.loads((folder/'walk_forward'/f'{REFERENCE_RUN}.json').read_text())
        stress = json.loads((folder/'stress_mc'/f'{STRESS_RUN}.json').read_text())
    except FileNotFoundError as exc:
        raise ValueError('Historical strategy archive unavailable') from exc
    if walk['run_id'] != REFERENCE_RUN or stress['run_id'] != STRESS_RUN:
        raise ValueError('Historical strategy version mismatch')
    as_of = date.fromisoformat(stress['configuration']['as_of'])
    assets, intervals, x, rf, version = aligned(root, as_of, 'USD', 'core')
    if version != walk['data_version'] or version != stress['data_version']:
        raise ValueError('Historical input version mismatch')
    day = intervals[-1][1]
    signals = load_signals(root, as_of, assets, [day], version)
    macro = macro_signals(root, version, [day])
    keys = [k for k,v in walk['strategies'].items() if v['status']=='computed'
            and k not in SIGNED and stress['comparison'].get(k,{}).get('status')=='computed']
    with threadpool_limits(limits=1):
        targets = fit_models(keys,x[-60:],rf[-60:],assets,config(assets,.65,0.)[0].upper,
                             day,signals,seed=24,macro=macro.get(day))
    matrix, _ = scenario_matrix(assets,x,'USD')
    split = walk['development_months']
    result = {}
    for key in keys:
        target = targets[key]
        if target['status']!='computed':
            continue
        w = np.array(target['weights'],float)
        if not np.isfinite(w).all() or w.min() < -1e-9 or w.sum()>1+1e-7:
            continue
        full = np.r_[w,1-w.sum()]
        shocks = {k:float(full@v - (.02*abs(w).sum() if k=='margin_liquidity_shock' else 0))
                  for k,v in matrix.items()}
        archived = stress['comparison'][key]['scenarios']
        if any(abs(v-archived[k]['return'])>1e-7 for k,v in shocks.items()):
            continue
        returns = np.asarray(walk['strategies'][key]['returns'])
        if len(returns)!=len(walk['dates']) or not np.isfinite(returns).all():
            continue
        holdings = dict(zip([a['ticker'] for a in assets], w.tolist()))
        holdings['USD cash'] = max(0.,1-w.sum())
        result[key] = (holdings,shocks,returns)
    return result, split, np.asarray(walk['benchmarks']['sixty_forty']['returns'])


def cards(root, profile, aversion=None, goals=()):
    rows, split, _ = catalog(root)
    result = []
    for name,(weights,shocks,returns) in rows.items():
        loss = max(0.,-min(shocks.values()))
        if loss <= profile.max_stress_loss + 1e-10:
            result.append(dict(name=name, version=VERSION, weights=weights, period=PERIOD,
                               costs=COSTS, stress_loss=loss, stress_usd=loss*profile.capital,
                               metrics=metrics(returns[split:,None],[1]), worst_scenario=min(shocks,key=shocks.get)))
    if aversion is not None and (isinstance(aversion,bool) or not isinstance(aversion,int) or not 1<=aversion<=30):
        raise ValueError('Invalid discovery score')
    defensive={'OBJ01','OBJ03','OBJ11'}
    growth={'OBJ05','OBJ06'}
    preference = sum(g['priority']*(int(g['objective_id'] in defensive)-int(g['objective_id'] in growth))
                     for g in goals)/max(1,sum(g['priority'] for g in goals))
    risk_weight = np.clip(.5+.2*preference+(.25*(aversion-15.5)/14.5 if aversion else 0),.05,.95)
    for p in result:
        dev=rows[p['name']][2][:split]
        growth_score=float(np.clip((12*dev.mean()+.05)/.20,0,1))
        risk_score=1-p['stress_loss']/max(profile.max_stress_loss,1e-10)
        p['fit_score']=float(risk_weight*risk_score+(1-risk_weight)*growth_score)
        p['fit_risk_weight']=float(risk_weight)
        p['development_return']=float(12*dev.mean())
    for p in result:
        p['pareto']=not any(q['stress_loss']<=p['stress_loss'] and q['development_return']>=p['development_return']
                            and (q['stress_loss']<p['stress_loss'] or q['development_return']>p['development_return'])
                            for q in result)
    return sorted(result,key=lambda p:(not p['pareto'],-p['fit_score'],p['name']))


def blend(root,profile,names,budgets,optimized):
    rows,split,reference = catalog(root)
    eligible = {p['name'] for p in cards(root,profile)}
    if not isinstance(names,list) or not names or len(names)!=len(set(names)) or not set(names)<=eligible:
        raise ValueError('Ineligible or stale selection')
    paths = np.column_stack([rows[k][2] for k in names])
    alpha = np.ones(len(names))/len(names)
    if optimized and len(names)>1:
        cov = np.cov(paths[:split].T)*12
        solution = minimize(lambda a: float(a@cov@a),alpha,jac=lambda a:2*cov@a,
                            bounds=[(0,1)]*len(alpha),constraints=[dict(type='eq',fun=lambda a:a.sum()-1)],
                            method='SLSQP',options={'ftol':1e-12,'maxiter':500})
        if not solution.success:
            raise ValueError('Optimization failed')
        alpha = solution.x
    elif not optimized:
        alpha = np.asarray(budgets,float)
    if alpha.shape!=(len(names),) or not np.isfinite(alpha).all() or alpha.min() < -1e-10 or abs(alpha.sum()-1)>1e-8:
        raise ValueError('Allocations must total 100%')
    alpha = np.maximum(alpha,0)
    alpha /= alpha.sum()
    weights = {a:sum(v*rows[k][0][a] for k,v in zip(names,alpha)) for a in rows[names[0]][0]}
    shocks = {s:sum(v*rows[k][1][s] for k,v in zip(names,alpha)) for s in rows[names[0]][1]}
    loss = max(0.,-min(shocks.values()))
    if loss>profile.max_stress_loss+1e-9:
        raise ValueError('Combined stress exceeds mandate')
    from riskmatch.selection.sleeve_ledger import rebalance_paths
    components,fees,turnover=rebalance_paths(paths[split:],alpha)
    net=components.sum(axis=1)
    cov = np.atleast_2d(np.cov(components,rowvar=False))*12
    vol = np.sqrt(max(0.,cov.sum()))
    rc = cov.sum(axis=1)/vol if vol else np.zeros_like(alpha)
    sleeve_cov=np.atleast_2d(np.cov(paths[split:],rowvar=False))
    denom=np.sqrt(np.outer(sleeve_cov.diagonal(),sleeve_cov.diagonal()))
    correlations=np.divide(sleeve_cov,denom,out=np.zeros_like(sleeve_cov),where=denom>0)
    overlap=[a for a in weights if sum(v*rows[k][0][a]>1e-8 for k,v in zip(names,alpha))>1]
    return dict(status='historical_research',version=VERSION,period=PERIOD,costs=COSTS,
                budgets=dict(zip(names,alpha.tolist())),weights=weights,metrics=metrics(net[:,None],[1]),
                allocation_metrics_version="net-sleeve-transfer-v1",
                additional_transfer_fee_fraction=float(fees.sum()),additional_transfer_turnover=float(turnover.mean()*12),
                risk_contributions=dict(zip(names,rc.tolist())),stress_loss=loss,stress_usd=loss*profile.capital,
                scenarios=shocks,reference_metrics=metrics(reference[split:,None],[1]),paper_only=True,
                correlations=correlations.tolist(),overlap=overlap)
