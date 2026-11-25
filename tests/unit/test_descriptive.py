import numpy as np
import pytest

from riskmatch.analytics.descriptive import (
    summarize,distribution,time_diagnostics,covariance_matrix,portfolio_variance,
    training_transform,rolling_statistics,
)


def test_sample_statistics_and_missingness():
    result=summarize([.1,.2,.3,np.nan],12)
    assert result["count"]==3 and result["missing"]==1
    assert result["mean"]==pytest.approx(.2)
    assert result["variance"]==pytest.approx(.01)
    assert result["annualized_volatility"]==pytest.approx(.1*np.sqrt(12))
    assert summarize([-.1,.1])["downside_deviation"]==pytest.approx(.1/np.sqrt(2))
    plots=distribution([0,0,1])
    assert sum(row[2] for row in plots["histogram"])==3
    assert plots["cdf"][0]==[0,2/3]


def test_covariance_psd_and_constants():
    result=covariance_matrix([[1,2,7],[2,4,7],[3,6,7],[np.nan,9,7]])
    assert result["count"]==3 and result["psd"]
    assert np.array(result["covariance"])==pytest.approx(np.array([[1,2,0],[2,4,0],[0,0,0]]))
    assert result["pearson"][0][1]==pytest.approx(1)
    assert result["spearman"][1][2] is None
    assert portfolio_variance(result["covariance"],[.5,.5,0])==pytest.approx(2.25)
    assert covariance_matrix([[1,np.nan]])["covariance"] is None


def test_training_and_rolling_do_not_use_future():
    x=[.01,.02,-.01,.03,.05,.06]
    b=[.02,.04,-.02,.06,.1,.12]
    assert rolling_statistics(x,b,3,252)[:4]==rolling_statistics(x[:4]+[99,100],b,3,252)[:4]
    assert rolling_statistics(x,b,3,252)[3]["beta"]==pytest.approx(.5)
    assert rolling_statistics([.1,np.nan,.3],b[:3],3,252)[-1]["mean"] is None
    train=[-.2,-.1,.1,.2]
    assert training_transform(train,[1])[0]==pytest.approx(training_transform(train,[1,9999])[0])


def test_serial_diagnostics():
    rng=np.random.default_rng(10)
    x=rng.normal(size=100)
    result=time_diagnostics(x)
    assert len(result["acf"])==11 and len(result["pacf"])==11
    assert 0<=result["ljung_box_p"]<=1
    assert np.isfinite(result["adf_lag1_t"])
    assert time_diagnostics(np.ones(100))["acf"]==[]
