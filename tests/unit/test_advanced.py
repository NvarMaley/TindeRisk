import numpy as np
import pytest
from riskmatch.optimization.advanced import block_draws,uncertainty,quadratic,robust_utility,resampled_utility,wasserstein_utility,kelly,entropy_utility


def fixture():
    mu=np.array([.08,.12]);cov=np.array([[.04,.018],[.018,.09]]);u=np.ones(2);ref=np.array([.5,.5]);return mu,cov,u,ref


def test_zero_radius_and_covariance_uncertainty():
    mu,cov,u,ref=fixture();a=quadratic(mu,cov,u,3,.001,ref);b=robust_utility(mu,cov,np.zeros(2),0,u,3,.001,ref);d=wasserstein_utility(mu,cov,0,u,3,.001,ref)
    assert a['status']==b['status']==d['status']=='optimal';assert b['weights']==pytest.approx(a['weights'],abs=1e-5);assert d['weights']==pytest.approx(a['weights'],abs=1e-5)
    r=robust_utility(mu,cov,np.array([.01,.03]),.02,u,3,.001,ref);assert r['status']=='optimal';w=np.array(r['weights']);assert r['worst_expected_return']==pytest.approx((mu-[.01,.03])@w);assert r['worst_variance']>w@cov@w


def test_bootstrap_and_aggregate():
    x=np.random.default_rng(2).normal(.01,.03,(36,3));a=block_draws(36,5);assert np.array_equal(a,block_draws(36,5));assert np.all(np.diff(a[:,:3],axis=1)==1)
    mu,cov,h,r,means,covs=uncertainty(x,5);assert np.all(h>=0) and r>=0
    u=np.full(3,.6);q=resampled_utility(means,covs,u,3,0,np.ones(3)/3);assert q['status']=='aggregated_feasible';assert sum(q['weights'])==pytest.approx(1);assert max(q['weights'])<=.600001


def test_kelly_floor_and_infeasibility():
    x=np.array([[-.999,.02],[.2,.01],[.1,-.01]]);r=kelly(x,[1,1],0,[.5,.5],.1);assert r['status']=='optimal';assert r['minimum_scenario_wealth']>=.1-1e-7
    assert kelly(np.full((3,2),-1.),[1,1],0,[.5,.5],.01)['status']=='infeasible'


def test_entropy_zero_weights_and_equal_case():
    r=entropy_utility(np.zeros(3),np.eye(3)*.05,.1,[1,1,1],1,0,[1/3]*3);assert r['status']=='optimal';assert r['weights']==pytest.approx([1/3]*3,abs=1e-5)
    r=entropy_utility(np.array([.1,.2,.3]),np.eye(3)*.05,.03,[.7,.7,0],1,.001,[.5,.5,0]);assert r['status']=='optimal';assert r['weights'][2]==0;assert np.isfinite(r['entropy'])
    r=entropy_utility(np.zeros(2),np.eye(2),.1,[.4,.6],1,0,[.4,.6]);assert r['status']=='optimal';assert r['weights']==pytest.approx([.4,.6])
