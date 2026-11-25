from datetime import date,timedelta
import numpy as np
import pytest
from riskmatch.analytics.factors import TAXONOMY,zscore,neutralize,factor_portfolio,regression,pca_diagnostics


def fixture():
    rng=np.random.default_rng(42)
    x=rng.normal(0,.02,(180,3))
    y=.001+x@np.array([1.2,.4,-.3])+rng.normal(0,.001,len(x))
    d=[date(2020,1,1)+timedelta(days=i) for i in range(len(x))]
    return y,x,d


def test_regression_attribution_and_training_isolation():
    y,x,d=fixture()
    r=regression(y,x,d,["Mkt-RF","SMB","HML"],"daily")
    assert r["beta"]["Mkt-RF"]==pytest.approx(1.2,abs=.03)
    assert r["beta"]["HML"]==pytest.approx(-.3,abs=.03)
    a=r["attribution"]
    assert a["alpha"]+sum(a["mean_factor_contribution"].values())+a["mean_residual"]==pytest.approx(a["mean_realized_excess"])
    changed=y.copy();changed[-20:]+=1
    q=regression(changed,x,d,["Mkt-RF","SMB","HML"],"daily")
    assert q["beta"]==r["beta"]
    assert q["ridge"]["alpha_penalty"]==r["ridge"]["alpha_penalty"]
    assert q["validation"]==r["validation"]
    with pytest.raises(ValueError,match="Rank-deficient"):regression(y,np.column_stack((x[:,0],x[:,0])),d,["a","b"],"daily")


def test_scores_and_missing_constituents():
    assert len(TAXONOMY)==13
    values=np.arange(100,dtype=float)
    scores=zscore(values)
    assert np.nanmean(scores)==pytest.approx(0,abs=1e-12)
    assert np.nanstd(scores,ddof=1)==pytest.approx(1)
    residual=neutralize(values,values)
    assert np.max(abs(residual))<1e-10
    ids=[str(i) for i in range(100)]
    gross=factor_portfolio(ids,scores,values/100,{},cost=0)
    assert gross["gross"]==pytest.approx(.8)
    bad=values.copy();bad[-1]=np.nan
    assert factor_portfolio(ids,scores,bad)["gross"] is None


def test_pca_diagnostics():
    _,x,_=fixture()
    report=pca_diagnostics(x)
    assert sum(report["explained_variance_ratio"])==pytest.approx(1)
    assert all(0<=v<=1+1e-12 for v in report["heldout_loading_similarity"])
