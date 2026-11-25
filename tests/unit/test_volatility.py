from datetime import date,timedelta
import numpy as np
import pytest

from riskmatch.analytics.volatility import (volatility_models,covariance_models,
    covariance_diagnostics,regularize,ewma_covariance,factor_covariance,dcc_correlation)


def sample():
    rng=np.random.default_rng(42)
    z=rng.multivariate_normal([0,0],[[1,.5],[.5,1]],size=700)
    h=np.full(2,.0004); r=[]
    for shock in z:
        e=np.sqrt(h)*shock;r.append(e)
        h=.00002+.12*e*e+.83*h
    return np.array(r),[date(2020,1,1)+timedelta(days=i) for i in range(len(r))]


def test_covariance_psd_shrinkage_and_leakage():
    x,_=sample()
    a=covariance_models(x,252)
    mutated=x.copy();mutated[-100:]*=3
    b=covariance_models(mutated,252)
    for m,v in a["models"].items():
        assert v["diagnostics"]["before"]["psd"]
        assert v["diagnostics"]["after"]["psd"]
        np.testing.assert_allclose(v["covariance"],b["models"][m]["covariance"])
        np.testing.assert_allclose(v["annualized_covariance"],np.array(v["covariance"])*252)
    assert np.allclose(ewma_covariance([[1,2],[3,4]],.5),[[5,7],[7,10]])
    corrected,diag=regularize([[1,1],[1,1]])
    assert diag["eigenvalues_adjusted"]==1 and covariance_diagnostics(corrected)["psd"]
    with pytest.raises(ValueError):regularize([[1,2],[2,1]])


def test_volatility_models_train_only_and_dcc():
    x,d=sample()
    a=volatility_models(x[:,0],d,252)
    assert {"historical","rolling","ewma","garch"}<=a["models"].keys()
    mutated=x[:,0].copy();mutated[-100:]*=3
    b=volatility_models(mutated,d,252)
    for name,v in a["models"].items():
        if name in b["models"]:
            assert v["validation"]["qlike"]==pytest.approx(b["models"][name]["validation"]["qlike"])
            assert v["annualized_volatility"]>=0
    dcc=dcc_correlation(x)
    assert dcc["diagnostics"]["psd"] and dcc["covariance_diagnostics"]["psd"]
    assert dcc["alpha"]+dcc["beta"]<1
    assert np.diag(dcc["next_correlation"])==pytest.approx([1,1])


def test_factor_covariance_reference():
    x,_=sample()
    out=factor_covariance(x,x[:,:1])
    assert covariance_diagnostics(out["diagonal_residual_covariance"])["psd"]
    assert np.allclose(out["full_residual_covariance"],np.cov(x,rowvar=False))
