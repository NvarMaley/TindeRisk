import numpy as np
import pandas as pd
import pytest

from src.client_allocation import reoptimize_for_client, resolve_client_exclusions
from src.optim import capped_erc, erc, vol
from src.profiling import RISK_BANDS


def diagonal(labels, values):
    return pd.DataFrame(np.diag(values), index=labels, columns=labels)


def test_capped_erc_recovers_the_unconstrained_solution_or_solves_at_the_cap():
    covariance = diagonal(["A", "B", "C"], [.0025, .04, .09])
    pd.testing.assert_series_equal(capped_erc(covariance, 1.), erc(covariance))
    weights = capped_erc(covariance, .45)
    assert weights["A"] == pytest.approx(.45, abs=1e-8)
    assert weights.sum() == pytest.approx(1.)
    assert (weights > 0).all()
    with pytest.raises(ValueError, match="infeasible"):
        capped_erc(covariance, .30)


@pytest.mark.parametrize("strategy", ["classic", "erc", "black_litterman"])
def test_reoptimization_respects_exclusions_cash_capacity_and_absolute_caps(strategy):
    covariance = diagonal(["A", "B", "C", "D"], [.03, .01, .04, .02])
    mean = pd.Series([.2, .15, .1, .06], index=covariance.columns)
    result = reoptimize_for_client(
        strategy, covariance, RISK_BANDS[-1], annual_excess_mean=mean, excluded_assets=["A"],
        max_etf_weight=.2, allow_borrowing=False, capacity_volatility=.08,
    )
    fit = result.allocation
    assert result.target_volatility == pytest.approx(.08)
    assert fit.risky_weights["A"] == 0
    assert fit.risky_weights.max() <= .2 + 1e-9
    assert fit.risky_weights.sum() + fit.cash_weight == pytest.approx(1.)
    assert fit.cash_weight >= .4 - 1e-9
    assert fit.achieved_volatility <= .08
    assert fit.achieved_volatility == pytest.approx(vol(fit.risky_weights, covariance))
    assert result.target_shortfall > 0


def test_connected_discards_views_touching_excluded_etfs():
    covariance = diagonal(["XLK", "XLE", "TLT"], [.04, .03, .01])
    p = pd.DataFrame([[1., -1., 0.]], index=["spread"], columns=covariance.columns)
    q = pd.Series([.2], index=p.index)
    omega = pd.DataFrame([[.004]], index=p.index, columns=p.index)
    settings = dict(excluded_assets=["XLE"], max_etf_weight=.35, allow_borrowing=True)
    connected = reoptimize_for_client("black_litterman", covariance, RISK_BANDS[1],
                                      views=(p, q, omega), **settings)
    balanced = reoptimize_for_client("erc", covariance, RISK_BANDS[1], **settings)
    assert connected.method == "connected_no_views"
    pd.testing.assert_series_equal(connected.allocation.risky_weights, balanced.allocation.risky_weights)


def test_connected_reoptimizes_an_active_view_with_the_etf_cap():
    covariance = diagonal(["A", "B", "C"], [.04, .04, .04])
    p = pd.DataFrame([[1., -1., 0.]], index=["spread"], columns=covariance.columns)
    q = pd.Series([.2], index=p.index)
    omega = pd.DataFrame([[.001]], index=p.index, columns=p.index)
    connected = reoptimize_for_client("black_litterman", covariance, RISK_BANDS[-1],
                                      views=(p, q, omega), max_etf_weight=.4, allow_borrowing=False)
    weights = connected.allocation.risky_weights
    assert connected.method == "connected"
    assert weights["A"] == pytest.approx(.4)
    assert weights["B"] < 1 / 3
    assert weights.max() <= .4 + 1e-9


def test_profile_exclusions_and_benchmark_filter_broad_equity():
    exclusions = resolve_client_exclusions(["energy", "gold"])
    assert exclusions == ("GLD", "SPY", "XLE")
    covariance = diagonal(["SPY", "IEF"], [.04, .01])
    fit = reoptimize_for_client("benchmark_60_40", covariance, RISK_BANDS[-1],
                               excluded_assets=exclusions, max_etf_weight=.25,
                               allow_borrowing=True).allocation
    assert fit.risky_weights.to_dict() == pytest.approx({"SPY": 0., "IEF": .25})
    assert fit.cash_weight == pytest.approx(.75)
    with pytest.raises(ValueError, match="no eligible ETF"):
        reoptimize_for_client("benchmark_60_40", covariance, RISK_BANDS[0],
                              excluded_assets=resolve_client_exclusions(["energy", "treasuries"]),
                              max_etf_weight=.25, allow_borrowing=False)
    with pytest.raises(ValueError, match="must be resolved"):
        resolve_client_exclusions(None)
