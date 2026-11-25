"""Chapter 25 research comparisons and synthetic shortlist allocation."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from riskmatch.prototype import ASSETS, VERSION, candidates, metrics, synthetic_returns


REFERENCE_RUN = '099ceda3c1c651997a4ee6d186e8cfcf93a9985192eecfb0b9ef33ece165a105'


def research_report(root):
    path = Path(root) / 'data/processed/walk_forward' / (REFERENCE_RUN + '.json')
    try:
        report = json.loads(path.read_text())
    except FileNotFoundError:
        return {'status': 'unavailable', 'reason': 'Frozen local research run missing'}
    if report['run_id'] != REFERENCE_RUN or report['version'] != 'walk-forward-v3':
        raise ValueError('Unexpected research version')
    start = report['development_months']
    dates = report['dates']
    reference = report['benchmarks']['sixty_forty']
    baseline = np.asarray(reference['returns'], float)
    if len(baseline) != len(dates):
        raise ValueError('Reference timeline mismatch')
    rows = []
    for key, strategy in report['strategies'].items():
        if strategy['status'] != 'computed' or len(strategy.get('returns', [])) != len(dates):
            continue
        paired = np.asarray(strategy['returns'], float) - baseline
        rows.append({'strategy': key, 'development_excess_annual': float(paired[:start].mean()*12),
                     'holdout_excess_annual': float(paired[start:].mean()*12),
                     'holdout_cagr': strategy['locked']['cagr'],
                     'holdout_volatility': strategy['locked']['annual_volatility'],
                     'holdout_drawdown': strategy['locked']['max_drawdown'],
                     'annual_turnover': strategy['annual_turnover'], 'sensitivity': strategy['sensitivity']})
    return {'status': 'experimental', 'run_id': REFERENCE_RUN, 'reference': '60% SPY / 40% IEF',
            'development_months': start, 'holdout_months': len(dates)-start,
            'reference_holdout': reference['locked'], 'strategies': rows,
            'excluded': {k: v.get('reason', 'Incomplete timeline') for k, v in report['strategies'].items()
                         if k not in {r['strategy'] for r in rows}},
            'warning': 'Previously examined holdout; retrospective comparison only. No causal ablation or independent approval.'}


def allocate(profile, names, budgets=None, optimize=False, version=VERSION):
    """Rebuild eligible synthetic sleeves server-side; never trust client weights."""
    available = {p['name']: p for p in candidates(profile)}
    if version != VERSION or not isinstance(names, list) or not names or len(set(names)) != len(names):
        raise ValueError('Invalid or stale Match selection')
    if any(name not in available for name in names):
        raise ValueError('Match is not eligible for this mandate')
    weights = np.array([[available[name]['weights'][a] for a in ASSETS] for name in names])
    train, test = np.split(synthetic_returns(), [84])
    if optimize:
        # Estimate covariance on training observations only; evaluate on held-out paths.
        covariance = np.cov(train @ weights.T, rowvar=False, ddof=1)
        covariance = np.atleast_2d(covariance)
        if len(names) == 1:
            alpha = np.ones(1)
        else:
            result = minimize(lambda a: float(a @ covariance @ a), np.ones(len(names))/len(names),
                              jac=lambda a: 2*covariance @ a, bounds=[(0, 1)]*len(names),
                              constraints=[{'type': 'eq', 'fun': lambda a: a.sum()-1}], method='SLSQP',
                              options={'ftol': 1e-12, 'maxiter': 500})
            if not result.success:
                raise ValueError('No feasible optimized allocation')
            alpha = result.x
    else:
        alpha = np.asarray(budgets, dtype=float)
    if alpha.shape != (len(names),) or not np.isfinite(alpha).all() or np.any(alpha < -1e-10) or abs(alpha.sum()-1) > 1e-8:
        raise ValueError('Match allocations must be nonnegative and total 100%')
    alpha = np.maximum(alpha, 0)
    alpha /= alpha.sum()
    consolidated = alpha @ weights
    loss = float(-np.array([-.30, -.12, -.35, 0]) @ consolidated)
    if loss > profile.max_stress_loss + 1e-10:
        raise ValueError('Combined stress exceeds mandate')
    sleeve_returns = test @ weights.T
    cov = np.atleast_2d(np.cov(sleeve_returns, rowvar=False, ddof=1))*12
    variance = float(alpha @ cov @ alpha)
    vol = np.sqrt(max(0., variance))
    risk = alpha*(cov @ alpha)/vol if vol > 0 else np.zeros_like(alpha)
    denom = np.sqrt(np.outer(np.diag(cov), np.diag(cov)))
    corr = np.divide(cov, denom, out=np.zeros_like(cov), where=denom > 0)
    return {'status': 'synthetic', 'version': VERSION, 'mode': 'minimum_variance' if optimize else 'manual',
            'budgets': dict(zip(names, alpha.tolist())), 'weights': dict(zip(ASSETS, consolidated.tolist())),
            'metrics': metrics(test, consolidated), 'stress_loss': loss, 'stress_usd': loss*profile.capital,
            'risk_contributions': dict(zip(names, risk.tolist())), 'correlations': corr.tolist(),
            'costs': 'Not modeled', 'paper_only': True}
