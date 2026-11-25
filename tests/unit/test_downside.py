import numpy as np
import pytest
from riskmatch.optimization.downside import tail,stats,cvar,cdar,sortino,omega,benchmark_models,negative_ratio


def test_cvar_fractional_and_lp():
    v,e=tail([0,1,2,8],[.25]*4,.625);assert v==2;assert e==pytest.approx((8*.25+2*.125)/.375)
    x=np.array([[.1,.05],[-.2,-.03],[.1,.05],[-.1,-.02]])
    r=cvar(x,[1,1],.75);assert r['status']=='optimal';assert r['weights']==pytest.approx([0,1]);assert r['cvar']==pytest.approx(.03)
    assert cvar(x,[1,1],.75,target=.2)['status']=='infeasible'


def test_additive_cdar_hand_calculation():
    x=np.array([[.1,.1],[-.2,-.02],[.05,.05],[-.1,-.01]])
    r=cdar(x,[1,1],.75);assert r['status']=='optimal';assert r['weights']==pytest.approx([0,1]);assert r['cdar']==pytest.approx(.02)
    assert stats(x[:,1])['maximum_drawdown']==pytest.approx(.02)


def test_positive_ratios_against_grid():
    x=np.array([[.12,.04],[-.04,-.02],[.06,.03],[-.02,-.01],[.03,.05]])
    for f,key in [(omega,'omega'),(sortino,'sortino')]:
        r=f(x,[1,1]);assert r['status']=='optimal';values=[stats(x@np.array([w,1-w]))[key] for w in np.linspace(0,1,2001)];assert r[key]>=max(values)-1e-5
    for f in (omega,sortino):assert f(np.ones((4,2))*.01,[1,1])['status']=='zero_downside'


def test_negative_ratio_and_benchmark_identity():
    x=np.array([[.04,.01],[-.02,-.04],[.03,.01],[-.01,-.02]])
    c=np.diag([.04,.09]);te,ir=benchmark_models(x,[1,1],[1,0],c);assert te['status']=='optimal';assert te['volatility']<1e-6;assert ir['status']=='optimal';assert ir['sharpe']<=0
    r=negative_ratio([.65,.65],[-.1,-.2],lambda w:np.linalg.norm(w),'test');assert r['status']=='optimal';assert r['ratio_raw']<0
    assert stats(x[:,0],benchmark=x[:,0])['information_ratio'] is None
    for f in (omega,sortino):assert f(-np.abs(x),[1,1])['status']=='optimal'
