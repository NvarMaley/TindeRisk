import numpy as np
import pytest
from riskmatch.optimization.hierarchical import risk_budget,risk_contributions,hierarchy,hrp,herc,maximum_diversification,proportional_cap,describe


def test_equal_uncorrelated_and_euler():
    c=np.eye(4)*.04;r=risk_budget(c);assert r['status']=='optimal';assert r['weights']==pytest.approx(np.ones(4)/4)
    t=hierarchy(c);assert hrp(c,t)==pytest.approx(np.ones(4)/4);h=herc(c,t,2);assert h['status']=='optimal';assert h['cluster_risk_shares']==pytest.approx([.5,.5],abs=2e-5)
    m=maximum_diversification(c,np.ones(4));assert m['status']=='optimal';assert m['weights']==pytest.approx(np.ones(4)/4,abs=1e-5);assert m['diversification_ratio']==pytest.approx(2)
    r=risk_contributions(c,np.array([.25]*4));assert sum(r['contributions'])==pytest.approx(r['volatility']);assert sum(r['shares'])==pytest.approx(1)


def test_unequal_risk_and_user_budgets():
    c=np.diag([.04,.09]);r=risk_budget(c);assert r['weights']==pytest.approx([.6,.4],abs=1e-5)
    r=risk_budget(c,[.8,.2]);assert risk_contributions(c,r['weights'])['shares']==pytest.approx([.8,.2],abs=2e-5)
    w,changed=proportional_cap(r['weights'],[.6,.8]);assert changed and w==pytest.approx([.6,.4]);assert describe(c,w,[.8,.2])['budget_error']>0
    q=risk_budget(c,[.8,.2],upper=[.6,.8]);assert q['status']=='constrained_optimal';assert q['weights']==pytest.approx([.6,.4],abs=1e-6);assert q['kkt_residual']<2e-4
    with pytest.raises(ValueError):proportional_cap([.5,.5],[.4,.4])
    with pytest.raises(ValueError):risk_budget(c,[.4,.4])


def test_perfect_correlation_and_duplicates():
    c=np.full((3,3),.04);t=hierarchy(c,'complete',['A','B','C']);assert t['duplicate_pair_count']==3;assert np.isfinite(t['linkage']).all();assert hrp(c,t).sum()==pytest.approx(1)
    assert risk_budget(c)['status']=='optimal';assert maximum_diversification(c,np.ones(3))['diversification_ratio']==pytest.approx(1)
    with pytest.raises(ValueError):hierarchy(c,ids=['A','A','C'])
    with pytest.raises(ValueError):hierarchy([[1,2],[2,1]])


def test_zero_risk_and_signed_contribution():
    c=np.diag([.04,0]);assert risk_budget(c)['status']=='unavailable';assert maximum_diversification(c,np.ones(2))['status']=='unavailable'
    c=np.array([[.04,.03],[.03,.04]]);r=risk_contributions(c,[1.2,-.2]);assert r['shares'][1]<0;assert sum(r['shares'])==pytest.approx(1)
    c=np.array([[.04,.03,.0],[.03,.04,.001],[0,.001,.02]]);a=hierarchy(c,'single');b=hierarchy(c,'average');assert a['linkage'].shape==b['linkage'].shape
