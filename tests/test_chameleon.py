import numpy as np
import pandas as pd
import pytest

from src.chameleon import fit_chameleon, mix_regime_budgets
from src.optim import risk_contrib, vol


def sample():
    rng = np.random.default_rng(52)
    dates = pd.bdate_range("2019-01-01", periods=90)
    returns = pd.DataFrame(rng.normal(0, .015, (90, 3)), index=dates, columns=list("ABC"))
    filtered = pd.DataFrame(
        {"available_date": dates[[41, 60]], "state_0": [.25, 1.], "state_1": [.75, 0.]},
        index=dates[[40, 59]],
    )
    state_budgets = pd.DataFrame([[.8, .2], [.4, .6]], index=["state_0", "state_1"],
                                 columns=["equity", "bonds"])
    asset_groups = pd.Series({"A": "equity", "B": "equity", "C": "bonds"})
    return dates, returns, filtered, state_budgets, asset_groups


def test_chameleon_mixes_states_and_splits_group_share_across_etfs():
    dates, returns, filtered, budgets, groups = sample()
    fit = fit_chameleon(returns, filtered, budgets, groups, decision_date=dates[59], window=40)
    assert fit.regime_observation == dates[40]
    np.testing.assert_allclose(fit.group_budgets, [.5, .5], rtol=0, atol=1e-10)
    np.testing.assert_allclose(fit.asset_budgets, [.25, .25, .50], rtol=0, atol=1e-10)
    shares = risk_contrib(fit.weights, fit.annual_covariance) / vol(fit.weights, fit.annual_covariance)
    np.testing.assert_allclose(shares, fit.asset_budgets, rtol=0, atol=1e-9)
    following = fit_chameleon(returns, filtered, budgets, groups, decision_date=dates[60], window=40)
    assert following.regime_observation == dates[59]


def test_chameleon_ignores_future_probabilities_and_returns():
    dates, returns, filtered, budgets, groups = sample()
    prefix = fit_chameleon(returns.iloc[:60], filtered.iloc[:1], budgets, groups,
                           decision_date=dates[59], window=40)
    returns.iloc[60:] = .5
    filtered.loc[dates[59], ["state_0", "state_1"]] = [0., 1.]
    complete = fit_chameleon(returns, filtered, budgets, groups, decision_date=dates[59], window=40)
    pd.testing.assert_series_equal(prefix.weights, complete.weights)


def test_chameleon_requires_available_regimes_and_valid_budgets():
    dates, returns, filtered, budgets, groups = sample()
    with pytest.raises(ValueError, match="no filtered regime"):
        fit_chameleon(returns, filtered, budgets, groups, decision_date=dates[40], window=40)
    with pytest.raises(ValueError, match="sum to one"):
        mix_regime_budgets(pd.Series([.5, .6], index=budgets.index), budgets)
    with pytest.raises(ValueError, match="each budget group"):
        fit_chameleon(returns, filtered, budgets, groups.replace("bonds", "equity"),
                      decision_date=dates[59], window=40)
