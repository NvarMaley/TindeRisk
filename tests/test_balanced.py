import numpy as np
import pandas as pd
import pytest

from src.balanced import fit_balanced
from src.estimation import ledoit_wolf_constant_corr
from src.optim import risk_contrib, vol


@pytest.fixture
def returns():
    rng = np.random.default_rng(52)
    index = pd.bdate_range("2019-01-01", periods=90)
    values = rng.normal(0, [.018, .004, .015], (len(index), 3))
    return pd.DataFrame(values, index=index, columns=list("ABC"))


def test_balanced_uses_trailing_covariance_and_equal_risk_shares(returns):
    decision = returns.index[59]
    fit = fit_balanced(returns, decision_date=decision, window=40)
    covariance, _ = ledoit_wolf_constant_corr(returns.iloc[20:60])
    pd.testing.assert_frame_equal(fit.annual_covariance, covariance)
    assert (fit.weights > 0).all()
    assert fit.weights.sum() == pytest.approx(1)
    shares = risk_contrib(fit.weights, covariance) / vol(fit.weights, covariance)
    np.testing.assert_allclose(shares, np.full(3, 1 / 3), atol=1e-9, rtol=0)
    assert fit.weights["B"] > .35


def test_balanced_history_excludes_observations_after_decision(returns):
    decision = returns.index[59]
    prefix = fit_balanced(returns.iloc[:60], decision_date=decision, window=40)
    returns.iloc[60:] *= 100
    extended = fit_balanced(returns, decision_date=decision, window=40)
    pd.testing.assert_series_equal(prefix.weights, extended.weights)
    pd.testing.assert_frame_equal(prefix.annual_covariance, extended.annual_covariance)


def test_balanced_requires_an_observed_close_and_a_complete_window(returns):
    with pytest.raises(ValueError, match="close must belong"):
        fit_balanced(returns, decision_date=pd.Timestamp("2019-01-05"), window=40)
    with pytest.raises(ValueError, match="insufficient trailing history"):
        fit_balanced(returns, decision_date=returns.index[38], window=40)
