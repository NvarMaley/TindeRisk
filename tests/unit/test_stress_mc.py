import numpy as np
import pytest
from riskmatch.simulation.stress_mc import paths,project,covariance_model,MODELS,rebalance,pay
from riskmatch.simulation.stress_report import scenario_matrix,schedule


def test_normal_covariance_and_seed():
    rng=np.random.default_rng(7);x=rng.multivariate_normal([.01,.005,0],[[.002,.001,0],[.001,.002,0],[0,0,.0001]],size=120);a,_=next(paths(x,1,10000,'normal',seed=3));b,_=next(paths(x,1,10000,'normal',seed=3));np.testing.assert_array_equal(a,b);m,_,_,cov=covariance_model(x);np.testing.assert_allclose(a.mean(0),m,atol=.002);np.testing.assert_allclose(np.cov(a,rowvar=False),cov,atol=.0001)


def test_all_models_deterministic_zero_volatility():
    x=np.zeros((40,3));events={0:[(1.,'contribution',10.)]};goals={1:[(1.,{'index':0,'date':'2028-01-01','target':110.,'funding':False,'priority':1})]}
    for model in MODELS:
        r=project(paths(x,2,100,model),np.array([1.,0.]),100,2,100,events,goals,cost_bps=0,inflation=0)
        assert r['percentiles']==[110.]*5 and r['goals'][0]['probability']==1


def test_dated_goal_funding_and_fee_cash():
    gen=((np.zeros((10,2)),0) for _ in range(2));events={0:[(.5,'withdrawal',20.)]};goals={1:[(1.,{'index':0,'date':'2028-01-01','target':100.,'funding':True,'priority':1})]}
    r=project(gen,np.array([0.]),100,2,10,events,goals,cost_bps=10,inflation=0)
    assert r['percentiles']==[0.]*5 and r['expected_unmet_cash']==pytest.approx(20) and r['mean_fees']==0 and r['goals'][0]['probability']==0
    h=np.array([[100.,0.]]);new,fee=rebalance(h,np.array([0.,1.]),.01);assert new.sum()+fee[0]==pytest.approx(100)


def test_goal_priority_and_joint_success():
    gg={0:[(1.,{'index':1,'date':'2027-01-01','target':50.,'funding':True,'priority':1}),(1.,{'index':0,'date':'2027-01-01','target':80.,'funding':True,'priority':5})]}
    r=project(iter([(np.zeros((100,2)),0)]),np.array([0.]),100,1,100,{},gg,cost_bps=0,inflation=0)
    assert r['goals'][0]['index']==0 and r['goals'][0]['probability']==1 and r['goals'][1]['expected_deficit']==30 and r['all_targeted_goals_probability']==0


def test_block_sampling_preserves_sequences():
    x=np.c_[np.arange(30)*.001,np.zeros(30)];a=np.stack([r[:,0] for r,_ in paths(x,6,100,'block_bootstrap',block=6)],axis=1);np.testing.assert_allclose(np.diff(a,axis=1),.001)


def test_short_squeeze_and_insolvency():
    r=project(iter([(np.array([[0.,3.,0.]]),0)]),np.array([.5,-.5]),100,1,1,{}, {},cost_bps=0,inflation=0,borrow_bps=0)
    assert r['insolvency_probability']==1 and r['expected_insolvency_debt']==pytest.approx(50)


def test_scenario_shocks_and_real_target():
    a=[{'ticker':'SPY','category':'equity_etf'},{'ticker':'IEF','category':'treasury_etf'},{'ticker':'TIP','category':'treasury_etf'}];b=np.linspace(-.03,.05,30);x=np.c_[b,b*.1,b*.05];r,_=scenario_matrix(a,x,'USD');assert r['equity_crash'][0]==pytest.approx(-.35);assert r['rates_up_200bp'][1]<0;assert r['real_yields_up_200bp'][2]<0;assert r['chf_appreciation'][0]==0
    r,_=scenario_matrix(a,x,'CHF');assert np.allclose(r['chf_appreciation'],-.1)
    s={'as_of':'2026-11-25','months':12,'capital':100,'inflation':.02,'contribution':0,'withdrawal':0,'target':100,'target_real':True};_,_,_,_,g,_=schedule(s);assert g[11][0][1]['target']==pytest.approx(102)
