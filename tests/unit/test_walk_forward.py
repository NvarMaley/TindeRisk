from datetime import date,timedelta
import numpy as np
import pytest
from riskmatch.backtesting.walk_forward import folds,ledger,bootstrap_comparison
from riskmatch.backtesting.walk_models import fit_models


def dates(n):
    d=date(2020,1,1);return [(d+timedelta(days=30*i),d+timedelta(days=30*(i+1))) for i in range(n)]


def test_fold_purge_and_lock():
    ff,h=folds(100,36,12,6,1,'rolling')
    assert ff[0].decision==50 and h==80
    assert all(f.train_end+1==f.validation_start and f.validation_end+1==f.decision for f in ff)
    assert all(f.test_end<=h for f in ff if f.phase=='development')
    assert next(f for f in ff if f.phase=='locked_holdout').decision==h
    assert ff[-1].test_end==100
    assert folds(100,36,12,6,1,'expanding')[0][-1].train_start==0


def test_delayed_execution_and_cash_reconcile():
    x=np.array([[.9,0],[.1,0],[.2,0]]);rf=np.zeros(3);u=np.ones_like(x)
    sim=ledger(x,rf,dates(3),{0:np.array([1.,0.])},u,capital=100,cost_bps=0,delay=1)
    np.testing.assert_allclose(sim['returns'],[0,.1,.2]);assert sim['final_nav']==pytest.approx(132)
    assert sim['trades'][0]['execution_date']==str(dates(3)[1][0])
    assert all(q['nav']==pytest.approx(q['asset_value']+q['cash']) for q in sim['ledger'])
    assert ledger(x,rf,dates(3),{},u,cost_bps=10)['final_nav']==pytest.approx(100)
    expensive=ledger(x,rf,dates(3),{0:np.array([1.,0.])},u,capital=100,cost_bps=100,delay=1)
    assert expensive['final_nav']<sim['final_nav']


def test_forced_exit_and_capacity():
    x=np.zeros((4,2));u=np.ones_like(x);u[2:,0]=0
    result=ledger(x,np.zeros(4),dates(4),{0:np.array([1.,0.])},u,cost_bps=0,delay=1)
    assert result['ledger'][2]['trade_reason']=='forced_eligibility_exit'
    assert result['ledger'][2]['cash']==pytest.approx(100)
    r=ledger(x,np.zeros(4),dates(4),{0:np.array([1.,0.])},u,cost_bps=0,delay=1,max_trade_notional=20)
    assert r['status']=='unavailable'
    r=ledger(x,np.zeros(4),dates(4),{1:np.array([1.,0.])},u,cost_bps=0,delay=1)
    assert r['ledger'][2]['trade_reason']=='scheduled_dropped_ineligible_to_cash'


def test_signed_borrow_and_no_double_counting():
    x=np.array([[0.,0.],[.1,-.1],[0.,0.]]);u=np.ones_like(x);p={0:np.array([.5,-.5])}
    r=ledger(x,np.zeros(3),dates(3),p,u,cost_bps=0,delay=1,signed=True,borrow_bps=0.)
    assert r['final_nav']==pytest.approx(110.)
    b=ledger(x,np.zeros(3),dates(3),p,u,cost_bps=0,delay=1,signed=True,borrow_bps=1200.)
    assert b['final_nav']<110 and b['borrow_cost']>0
    assert b['ledger'][1]['asset_value']+b['ledger'][1]['cash']==pytest.approx(b['ledger'][1]['nav'])


def test_future_perturbation_and_joint_bootstrap():
    rng=np.random.default_rng(3);x=rng.normal(.007,.02,(60,5));names=['SPY','SHY','IEF','BIL','TIP'];a=[{'id':t,'ticker':t,'source':'etf_crsp_monthly','category':'equity_etf' if t=='SPY' else 'treasury_etf'} for t in names];u=np.full(5,.65);r=np.zeros(60);args=(['minimum_variance','mean_variance_utility'],x[:36],r[:36],a,u,date(2024,1,1),({}, {}, {}));w=fit_models(*args);x[36:]=5;v=fit_models(*args)
    for k in w:np.testing.assert_allclose(w[k]['weights'],v[k]['weights'])
    b=np.zeros(20);rows={'a':np.ones(20)*.01,'b':np.zeros(20)};assert bootstrap_comparison(rows,b)==bootstrap_comparison(rows,b)
