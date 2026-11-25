"""Paired chapter 25 core-USD experiments on frozen chapter 23 dates."""
from datetime import date
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from riskmatch.backtesting.walk_forward import folds, ledger, bootstrap_comparison
from riskmatch.optimization.mean_variance_report import aligned
from riskmatch.matching import REFERENCE_RUN


@lru_cache(maxsize=2)
def compare_variants(root):
    frozen = json.loads((Path(root)/'data/processed/walk_forward'/f'{REFERENCE_RUN}.json').read_text())
    s = frozen['configuration']
    assets, dates, x, rf, version = aligned(root,date.fromisoformat(s['as_of']),'USD','core')
    windows, hold = folds(len(x),s['train'],s['validation'],s['step'],s['embargo'],s['mode'])
    first = windows[0].decision
    if version!=frozen['data_version'] or [str(b) for _,b in dates[first:]]!=frozen['dates']:
        raise ValueError('Reference dates or observations changed')
    k = len(assets)
    reference = np.asarray(frozen['benchmarks']['sixty_forty']['returns'])
    split = hold-first
    variants = {}
    paths = {}
    for name in ('reference_model','empirical_covariance','ewma_mean','tighter_cap','turnover_penalty','robust_mean'):
        targets = {}
        previous = np.ones(k)/k
        cap = .4 if name=='tighter_cap' else .65
        for f in windows:
            h = x[f.train_start:f.validation_end]
            mu = (np.average(h,axis=0,weights=.94**np.arange(len(h)-1,-1,-1))
                  if name=='ewma_mean' else h.mean(axis=0))*12
            cov = (np.cov(h.T) if name=='empirical_covariance' else LedoitWolf().fit(h).covariance_)*12
            if name=='robust_mean':
                mu -= 12*h.std(axis=0,ddof=1)/np.sqrt(len(h))
            def objective(w):
                penalty=.005*abs(w-previous).sum() if name=='turnover_penalty' else 0.
                return float(3*w@cov@w - mu@w + penalty)
            fit = minimize(objective,previous,bounds=[(0,cap)]*k,
                           constraints=[dict(type='eq',fun=lambda w:w.sum()-1)],method='SLSQP',
                           options={'ftol':1e-10,'maxiter':500})
            if not fit.success:
                raise ValueError('Variant optimization failed: '+name)
            previous = fit.x
            targets[f.decision-first] = previous
        result = ledger(x[first:],rf[first:],dates[first:],targets,np.full_like(x[first:],cap),
                        capital=s['capital'],cost_bps=s['cost_bps'],delay=s['delay'])
        if result['status']!='computed':
            raise ValueError(result['reason'])
        ret = result['returns']
        paths[name] = ret[split:]
        variants[name] = {'development_excess':float(12*(ret-reference)[:split].mean()),
                          'holdout_excess':float(12*(ret-reference)[split:].mean()),
                          'holdout_volatility':float(np.std(ret[split:],ddof=1)*np.sqrt(12)),
                          'annual_turnover':result['annual_turnover']}
    base = paths['reference_model']
    for name,r in paths.items():
        variants[name]['paired_change_vs_model'] = float((r-base).mean()*12)
    return {'status':'experimental','variants':variants,'holdout_months':len(base),
            'uncertainty':bootstrap_comparison(paths,base),'reference_run':REFERENCE_RUN}
