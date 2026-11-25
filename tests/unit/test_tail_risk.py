import numpy as np
import pytest
from riskmatch.analytics.tail_risk import empirical, contributions, drawdown, profile, dependence, currency_loss


def test_loss_conventions_and_invalid_confidence():
    assert currency_loss(.05,100000)==5000
    assert currency_loss(-.05,100000)==-5000
    for sample,alpha in [([], .95),([1,np.nan],.95),([1],1),([1],0)]:
        with pytest.raises(ValueError):empirical(sample,alpha)
    with pytest.raises(ValueError):contributions([[0,0]],[.5,.5],0)


def test_fractional_es_and_ties():
    x=[0,1,2,2,8]
    m=empirical(x,.7)
    assert m['var']==2
    assert m['es']==pytest.approx((8+.5*2)/1.5)
    a=contributions(-np.array([[1,0],[0,1],[0,0]]),[.5,.5],.5)
    assert sum(a['contributions'])==pytest.approx(a['es'])
    assert a['contributions'][0]==pytest.approx(a['contributions'][1])


def test_drawdown_and_zero():
    d=drawdown([.1,-.5,1],['a','b','c'])
    assert d['maximum']==pytest.approx(.5)
    assert d['recovery_periods']==1
    p=profile(np.zeros(100),range(100))
    assert p['models']['95']['historical']=={'var':0.,'es':0.}
    assert not p['models']['99']
    assert profile([.1,-1],range(2))['drawdown']['maximum']==1
    with pytest.raises(ValueError):profile([0,np.nan],range(2))
    assert not profile([.1,.2],range(2),False)['models']
    assert profile([.01,.03],range(2),False,target=.02)['shortfall_probability']==.5


def test_aligned_copulas():
    rng=np.random.default_rng(3);x=rng.normal(0,.02,(600,2));x[:,1]+=.5*x[:,0]
    p=dependence(x)
    assert p['student_t_lower_upper_tail'][0][1]>0
    assert sum(p['es_contributions']['contributions'])==pytest.approx(p['es_contributions']['es'])
    assert p['test_observations']==180
    with pytest.raises(ValueError):dependence(np.ones((200,2)))
