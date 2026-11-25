import numpy as np
import pytest
from riskmatch.optimization.black_litterman import posterior,equilibrium,delta_estimate
from riskmatch.optimization.black_litterman_report import manual_views

C=np.diag([.04,.09]);W=np.array([.6,.4]);D=2.;T=.05


def test_no_view_and_analytical_one_view():
    pi=equilibrium(C,W,D);a=posterior(C,W,D,T)
    assert a['posterior_excess']==pytest.approx(pi)
    assert a['predictive_covariance']==pytest.approx(C*(1+T))
    p=posterior(C,W,D,T,[[1,0]],[.1],[.5]);assert p['posterior_excess'][0]==pytest.approx((pi[0]+.1)/2)
    assert p['posterior_excess'][1]==pytest.approx(pi[1]);assert p['mean_covariance'][0,0]==pytest.approx(T*C[0,0]/2)


def test_weak_strong_and_exact():
    a=posterior(C,W,D,T,[[1,-1]],[.02],[.1]);b=posterior(C,W,D,T,[[1,-1]],[.02],[.9]);z=posterior(C,W,D,T,[[1,-1]],[.02],[1.])
    assert abs(np.array([1,-1])@b['posterior_excess']-.02)<abs(np.array([1,-1])@a['posterior_excess']-.02)
    assert np.array([1,-1])@z['posterior_excess']==pytest.approx(.02);assert z['residual']<1e-8
    assert np.linalg.eigvalsh(z['mean_covariance']).min()>-1e-10


def test_duplicates_conflicts_and_correlated_views():
    a=posterior(C,W,D,T,[[1,0],[2,0]],[.1,.2],[.5,.5]);b=posterior(C,W,D,T,[[1,0]],[.1],[.5]);assert a['posterior_excess']==pytest.approx(b['posterior_excess']);assert len(a['dropped_views'])==1
    with pytest.raises(ValueError):posterior(C,W,D,T,[[1,0],[-1,0]],[.1,.1],[.5,.5])
    with pytest.raises(ValueError):posterior(C,W,D,T,[[1,0],[0,1],[1,1]],[.1,.2,.5],[1,1,1])
    a=posterior(C,W,D,T,[[1,0],[0,1]],[.1,.2],[.5,.5],[[1,.6],[.6,1]]);assert a['omega'][0,1]>0
    with pytest.raises(ValueError):posterior(C,W,D,T,[[1,0],[0,1]],[.1,.2],[.5,.5],[[1,2],[2,1]])


def test_singular_zero_confidence_and_units():
    z=posterior(np.zeros((2,2)),W,D,T,[[1,0]],[0],[1]);assert z['rank']==0
    with pytest.raises(ValueError):posterior(np.zeros((2,2)),W,D,T,[[1,0]],[.1],[1])
    a=posterior(C,W,D,T,[[1,0]],[.1],[0]);assert a['posterior_excess']==pytest.approx(equilibrium(C,W,D))
    P,q,_,_,_=manual_views([{'id':'A'},{'id':'B'}],[{'type':'absolute','asset':'A','return':.1,'confidence':.5},{'type':'relative','asset':'A','relative_to':'B','return':.02,'confidence':.5}],.03)
    assert q==pytest.approx([.07,.02]);assert P[1]==pytest.approx([1,-1]);assert delta_estimate(np.zeros((10,2)),np.ones(10)*.001,W)['source']=='declared_fallback_positive_delta'
