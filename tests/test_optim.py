import numpy as np
import pandas as pd
import pytest

from src.optim import bl_posterior, erc, risk_budget, risk_contrib, target_vol, tracking_error, vol


def covariance(values):
    return pd.DataFrame(values, index=["A", "B"], columns=["A", "B"])


def test_euler_decomposition_and_active_volatility():
    sigma = covariance([[.04, .006], [.006, .01]])
    weights = pd.Series({"A": .45, "B": .55})
    reference = pd.Series({"A": .60, "B": .40})
    assert risk_contrib(weights, sigma).sum() == pytest.approx(vol(weights, sigma))
    assert tracking_error(weights, reference, sigma) == pytest.approx(.15 * np.sqrt(.038))
    assert tracking_error(weights, weights, sigma) == 0
    with pytest.raises(ValueError, match="labels"):
        tracking_error(weights, reference.iloc[::-1], sigma)


def test_risk_budget_matches_unequal_targets_and_erc_diagonal_solution():
    sigma = covariance([[.04, -.008], [-.008, .01]])
    budgets = pd.Series({"A": .25, "B": .75})
    weights = risk_budget(sigma, budgets)
    assert (weights > 0).all()
    assert weights.sum() == pytest.approx(1)
    assert (risk_contrib(weights, sigma) / vol(weights, sigma)).to_numpy() == pytest.approx(budgets.to_numpy())
    assert erc(covariance(np.diag([.04, .01]))).to_numpy() == pytest.approx([1 / 3, 2 / 3])
    assert erc(sigma * 252).to_numpy() == pytest.approx(erc(sigma).to_numpy())


def test_zero_budget_and_invalid_covariance_are_rejected():
    with pytest.raises(ValueError, match="strictly positive"):
        risk_budget(covariance(np.eye(2)), pd.Series({"A": 1., "B": 0.}))
    with pytest.raises(ValueError, match="positive definite"):
        erc(covariance(np.ones((2, 2))))
    with pytest.raises(ValueError, match="positive semidefinite"):
        vol(pd.Series({"A": 1., "B": 0.}), covariance([[1, 2], [2, 1]]))


def test_bl_prior_identity_and_confidence():
    sigma = covariance([[.04, .006], [.006, .01]])
    prior = pd.Series({"A": .055, "B": .035}, name="annual_excess_mean")
    p = pd.DataFrame([[1., -1.]], index=["A-B"], columns=sigma.columns)
    q = pd.Series({"A-B": .04})
    empty = pd.DataFrame(dtype=float)
    result = bl_posterior(prior, sigma, p.iloc[:0], q.iloc[:0], empty, tau=.05)
    pd.testing.assert_series_equal(result, prior)
    spreads = []
    for variance in (.1, .0001):
        omega = pd.DataFrame([[variance]], index=p.index, columns=p.index)
        posterior = bl_posterior(prior, sigma, p, q, omega, tau=.05)
        spreads.append((p @ posterior).item())
    assert .02 < spreads[0] < spreads[1] < .04
    with pytest.raises(ValueError, match="Q labels"):
        bl_posterior(prior, sigma, p, q.rename(index={"A-B": "wrong"}), omega, tau=.05)


def test_target_vol_measures_actual_risk_after_caps():
    sigma = covariance(np.diag([.01, .01]))
    weights = pd.Series({"A": .6, "B": .4})
    cash = target_vol(weights, sigma, 0)
    assert cash.cash_weight == 1 and cash.achieved_volatility == 0
    levered = target_vol(weights, sigma, .08, max_risky_exposure=1.5)
    assert levered.cash_weight < 0
    assert levered.achieved_volatility == pytest.approx(.08)
    capped = target_vol(weights, sigma, .14, max_risky_exposure=1.5, max_etf_weight=.35)
    assert capped.risky_weights.max() == pytest.approx(.35)
    assert capped.cash_weight + capped.risky_weights.sum() == pytest.approx(1)
    assert capped.achieved_volatility == pytest.approx(vol(capped.risky_weights, sigma))
    assert capped.achieved_volatility < .14
