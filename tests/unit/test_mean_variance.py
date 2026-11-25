import numpy as np
import pytest
from riskmatch.optimization.mean_variance import MeanVariance,Constraints,analytic_min_variance
from riskmatch.optimization.mean_variance_report import regularized_mean


def model(mu=(.08,.12),cov=((.04,0),(0,.09)),rf=.02,**kwargs):
    return MeanVariance(mu,cov,rf,Constraints(np.zeros(2),np.ones(2),**kwargs))


def test_analytical_minimum_and_tangency():
    m=model();a=m.solve();assert a['status']=='optimal';assert a['weights']==pytest.approx([9/13,4/13],abs=1e-5)
    assert a['weights']==pytest.approx(analytic_min_variance(m.cov),abs=1e-5)
    t=m.max_sharpe();expected=np.linalg.solve(m.cov,m.mu-m.rf);expected/=expected.sum()
    assert t['status']=='optimal';assert t['weights']==pytest.approx(expected,abs=1e-4)
    assert sum(t['risk_contributions'])==pytest.approx(t['volatility'])


def test_frontier_and_utility():
    m=model();a,f=m.frontier(5);assert all(v['status']=='optimal' for v in f)
    assert np.all(np.diff([v['expected_return'] for v in f])>=-1e-8)
    assert np.all(np.diff([v['volatility'] for v in f])>=-1e-8)
    u=m.solve(return_weight=1,variance_weight=3);expected=(.08-.12+3*.09)/(3*(.04+.09))
    assert u['weights']==pytest.approx([expected,1-expected],abs=1e-5)
    assert m.solve(target=.13)['status']=='infeasible'


def test_singular_and_nonpositive_excess():
    m=model(cov=((.04,.04),(.04,.04)));assert m.solve()['status']=='optimal'
    assert model(rf=.2).max_sharpe()['status']=='unavailable'
    assert model(cov=((0,0),(0,0))).max_sharpe()['status']=='unbounded'
    with pytest.raises(ValueError):model(cov=((1,2),(2,1)))
    a=MeanVariance([.1,.2],np.eye(2),.02,Constraints(np.zeros(2),np.full(2,.4)))
    assert not a.feasible and a.solve()['status']=='infeasible'


def test_linear_gross_turnover_constraints():
    c=Constraints(np.array([-.3,-.3]),np.array([1.3,1.3]),gross=1.4,linear=[('issuer_or_group',np.array([1.,0.]),0,.7),('liquidity_factor',np.array([1.,2.]),1.2,2.)],previous=np.array([.5,.5]),turnover=.1,turnover_penalty=.005)
    m=MeanVariance([.20,.05],np.eye(2)*.04,.02,c);r=m.solve(return_weight=1,variance_weight=1)
    assert r['status']=='optimal';assert r['weights']==pytest.approx([.6,.4],abs=1e-5);assert r['gross']<=1.4;assert r['turnover']<=.100001;assert max(r['residuals'].values())<1e-7
    signed=MeanVariance([.2,-.1],np.eye(2)*.04,.02,Constraints(np.full(2,-.4),np.full(2,1.4),gross=1.4));a=signed.solve(return_weight=1,variance_weight=1);assert a['status']=='optimal';assert a['weights']==pytest.approx([1.2,-.2],abs=1e-5)


def test_turnover_penalty_and_mean_regularization():
    a=model(previous=np.array([.5,.5]),turnover_penalty=.1);b=a.solve(return_weight=1,variance_weight=1);assert b['weights']==pytest.approx([.5,.5],abs=1e-5)
    x=np.array([[.01,.02],[.02,.01]]);r=regularized_mean(x,[.9,-.9]);assert abs(r[0]-r[1])<10.8
