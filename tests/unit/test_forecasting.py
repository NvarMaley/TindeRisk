from datetime import date, timedelta
import json

import numpy as np
import pytest

from riskmatch.analytics.forecasting import forecast, lagged_examples, factor_reference, _bound


def fixture():
    r=np.random.default_rng(42).normal(.001,.02,220)
    d=[date(2020,1,1)+timedelta(days=i) for i in range(len(r))]
    return r,d


def run(r,d):
    return forecast(r,d,instrument="fixture",frequency="daily",currency="USD",
                    kind="total_return",data_version="synthetic-v1",as_of=d[-1])


def test_lags_and_test_isolation():
    r,d=fixture()
    X,y,_=lagged_examples(r)
    assert y[0]==r[20]
    assert X[0,0]==r[19]
    a=run(r,d)
    mutated=r.copy()
    mutated[-30:]+=1
    b=run(mutated,d)
    assert a["selected_model"]==b["selected_model"]
    for key,v in a["models"].items():
        assert v["parameters"]==b["models"][key]["parameters"]
        assert v["validation_mse"]==b["models"][key]["validation_mse"]
    assert a["bundle"]["horizon_periods"]==1
    assert a["approved"] is False
    json.dumps(a,allow_nan=False)


def test_constant_returns_and_invalid_dates():
    _,d=fixture()
    a=run(np.full(len(d),.005),d)
    assert a["models"]["historical"]["expected_return"]==pytest.approx(.005)
    assert a["models"]["historical"]["test"]["mae"]<1e-12
    assert a["models"]["ols"]["test"]["temporal_rank_correlation"] is None
    with pytest.raises(ValueError,match="Insufficient"):
        run(np.zeros(30),d[:30])
    with pytest.raises(ValueError,match="ordered"):
        run(np.zeros(len(d)),d[::-1])


def test_factor_reference_analytical():
    _,d=fixture()
    rng=np.random.default_rng(42)
    f=rng.normal(0,.02,(len(d),3))
    rf=np.full(len(d),.001)
    r=rf+.002+f@np.array([1.2,.4,-.3])
    result=factor_reference(r,f,rf,[.5,.5],np.eye(2)*.02)
    assert result["multifactor"]["beta"]==pytest.approx([1.2,.4,-.3])
    assert result["multifactor"]["alpha"]==pytest.approx(.002)
    assert result["black_litterman_no_view"]==pytest.approx([.025,.025])


def test_simple_return_economic_bound():
    assert _bound(np.array([-1.5,-.2,.1]),"total_return").tolist()==[-1.,-.2,.1]
    assert _bound(-1.5,"excess_return")==-1.5


def test_machine_learning_models_are_available_and_test_isolation():
    r,d=fixture()
    def run_ml(values):
        return forecast(values,d,instrument="fixture",frequency="daily",currency="USD",
                        kind="total_return",data_version="synthetic-v1",as_of=d[-1],include_ml=True)
    original=run_ml(r)
    changed=r.copy()
    changed[-30:]+=.25
    alternative=run_ml(changed)
    for name in ("random_forest","xgboost","neural_network"):
        assert name not in original["unavailable"]
        a,b=original["models"][name],alternative["models"][name]
        assert a["parameters"]["random_state"]==42
        assert a["parameters"]["library_version"]
        assert a["parameters"]==b["parameters"]
        assert a["validation_mse"]==pytest.approx(b["validation_mse"],abs=1e-12)
        assert len(a["history"])==original["split"]["test"]
        assert np.isfinite(a["test"]["mse"])
    json.dumps(original,allow_nan=False)
