import numpy as np
import pandas as pd
import pytest

from src.classic import classic_weights
from src.connected import connected_portfolio
from src.optim import erc, vol


@pytest.fixture
def inputs():
    covariance = pd.DataFrame([[.04, .006], [.006, .01]], columns=["A", "B"], index=["A", "B"])
    reference = erc(covariance)
    p = pd.DataFrame([[1., -1.]], index=["spread"], columns=covariance.columns)
    q = pd.Series([.08], index=p.index)
    omega = pd.DataFrame([[.001]], index=p.index, columns=p.index)
    return reference, covariance, p, q, omega


def test_no_views_return_reference_and_prior_exactly(inputs):
    reference, covariance, p, q, omega = inputs
    empty_views = {"p": p.iloc[:0], "q": q.iloc[:0], "omega": omega.iloc[:0, :0]}
    for kwargs in ({}, empty_views):
        fit = connected_portfolio(reference, covariance, reference_sharpe=.35, **kwargs)
        pd.testing.assert_series_equal(fit.weights, reference)
        pd.testing.assert_series_equal(fit.posterior_excess_mean, fit.prior_excess_mean)
        assert fit.annual_tracking_error == 0
        assert fit.tau is None
        assert reference @ fit.prior_excess_mean / vol(reference, covariance) == pytest.approx(.35)
        optimum, _ = classic_weights(fit.prior_excess_mean, covariance, 1.)
        np.testing.assert_allclose(optimum, reference, atol=1e-6, rtol=0)


def test_confidence_and_tracking_error_calibration(inputs):
    reference, covariance, p, q, omega = inputs
    strong = connected_portfolio(reference, covariance, reference_sharpe=.35, p=p, q=q, omega=omega)
    weak = connected_portfolio(reference, covariance, reference_sharpe=.35, p=p, q=q, omega=omega * 100)
    assert 0 < strong.tau < .05
    assert weak.tau == .05
    assert strong.annual_tracking_error == pytest.approx(.03, abs=1e-7)
    assert 0 < weak.annual_tracking_error < strong.annual_tracking_error
    assert strong.weights["A"] > weak.weights["A"] > reference["A"]
    assert strong.weights.min() >= 0 and strong.weights.sum() == pytest.approx(1)


def test_connected_rejects_incomplete_or_misaligned_views(inputs):
    reference, covariance, p, q, omega = inputs
    with pytest.raises(ValueError, match="provide P, Q, and Omega together"):
        connected_portfolio(reference, covariance, reference_sharpe=.35, p=p)
    with pytest.raises(ValueError, match="Q labels"):
        connected_portfolio(reference, covariance, reference_sharpe=.35,
                            p=p, q=q.rename(index={"spread": "other"}), omega=omega)


def test_ineligible_sentiment_flows_through_empty_views_to_the_erc_anchor(inputs):
    from src.signals import sentiment_view_matrix
    from src.view_returns import estimate_relative_q
    from src.view_uncertainty import estimate_omega

    reference, covariance, _, _, _ = inputs
    date = pd.Timestamp("2017-12-29")
    unapproved_scores = pd.Series({"A": .9, "B": -.9})
    p = sentiment_view_matrix(covariance.columns, covariance.columns, date, scores=unapproved_scores)
    active, q, diagnostics = estimate_relative_q(
        p, pd.DataFrame(), validation_start=None, final_test_start=None, decision_date=date
    )
    omega = estimate_omega(active, covariance, diagnostics, tau=.05)
    assert active.shape == (0, 2) and q.empty and omega.shape == (0, 0)
    result = connected_portfolio(reference, covariance, reference_sharpe=.35, p=active, q=q, omega=omega)
    pd.testing.assert_series_equal(result.weights, reference)
    pd.testing.assert_series_equal(result.posterior_excess_mean, result.prior_excess_mean)
    assert result.annual_tracking_error == 0
