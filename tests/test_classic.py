import numpy as np
import pandas as pd
import pytest

from src.baselines import minimum_variance_weights
from src.classic import classic_weights, fit_classic
from src.optim import vol


def test_uncapped_positive_tangency_matches_analytical_weights():
    mean = pd.Series({"A": .10, "B": .06})
    covariance = pd.DataFrame(np.diag([.04, .01]), index=mean.index, columns=mean.index)
    weights, method = classic_weights(mean, covariance, 1.)
    exact = np.linalg.solve(covariance, mean)
    assert method == "tangency"
    np.testing.assert_allclose(weights, exact / exact.sum(), rtol=0, atol=1e-6)


def test_capped_tangency_matches_a_grid_and_respects_weight_limits():
    mean = pd.Series({"A": .12, "B": .07, "C": -.02})
    covariance = pd.DataFrame([[.025, .008, .003], [.008, .04, .001], [.003, .001, .01]],
                              index=mean.index, columns=mean.index)
    cap = .5
    weights, method = classic_weights(mean, covariance, cap)
    first, second = np.meshgrid(np.linspace(0, cap, 101), np.linspace(0, cap, 101))
    grid = np.column_stack([first.ravel(), second.ravel(), (1 - first - second).ravel()])
    grid = grid[np.all((grid >= 0) & (grid <= cap), axis=1)]
    grid_sharpe = (grid @ mean.to_numpy()) / np.sqrt(np.einsum("ij,jk,ik->i", grid, covariance, grid))
    assert method == "tangency"
    assert weights.sum() == pytest.approx(1)
    assert weights.min() >= 0
    assert weights["A"] == pytest.approx(cap)
    assert weights @ mean / vol(weights, covariance) >= grid_sharpe.max() - 1e-8


def test_nonpositive_feasible_mean_uses_explicit_gmv_and_impossible_cap_errors():
    mean = pd.Series({"A": .02, "B": -.09, "C": -.03})
    covariance = pd.DataFrame(np.diag([.04, .06, .02]), index=mean.index, columns=mean.index)
    weights, method = classic_weights(mean, covariance, .5)
    assert method == "gmv_nonpositive"
    pd.testing.assert_series_equal(weights, minimum_variance_weights(covariance, .5))
    with pytest.raises(ValueError, match="infeasible maximum"):
        classic_weights(mean, covariance, .3)


def test_classic_at_close_ignores_future_observations():
    index = pd.bdate_range("2019-01-01", periods=90)
    rng = np.random.default_rng(52)
    returns = pd.DataFrame(rng.normal(.0015, .008, (len(index), 3)), index=index, columns=list("ABC"))
    excess = returns - .0001
    args = {"decision_date": index[59], "window": 40, "max_weight": .6}
    prefix = fit_classic(returns.iloc[:60], excess.iloc[:60], **args)
    returns.iloc[60:] = .20
    excess.iloc[60:] = -.20
    extended = fit_classic(returns, excess, **args)
    pd.testing.assert_series_equal(prefix.weights, extended.weights)
    pd.testing.assert_series_equal(prefix.annual_excess_mean, extended.annual_excess_mean)
    pd.testing.assert_frame_equal(prefix.annual_covariance, extended.annual_covariance)
    assert prefix.method == extended.method
