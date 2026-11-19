from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src import baselines, classic, optim
from src.client_allocation import reoptimize_for_client
from src.profiling import RISK_BANDS, volatility_band_position


def test_class_limits_apply_to_final_capital_and_support_zero_exposure():
    assets = ["XLK", "XLP", "IEF", "GLD"]
    covariance = pd.DataFrame(np.diag([.01, .01, .004, .006]), index=assets, columns=assets)
    mean = pd.Series([.10, .08, .06, .07], index=assets)
    for strategy in ("classic", "erc", "black_litterman"):
        fit = reoptimize_for_client(
            strategy, covariance, RISK_BANDS[-1], max_etf_weight=.35, allow_borrowing=True,
            annual_excess_mean=mean, class_weight_caps={"equity": .25, "gold": 0.},
        ).allocation
        weights = fit.risky_weights
        assert weights[["XLK", "XLP"]].sum() <= .25 + 1e-9
        assert weights["GLD"] == 0
        assert (weights >= 0).all() and weights.max() <= .35 + 1e-9
        assert weights.sum() + fit.cash_weight == pytest.approx(1.)
        assert fit.achieved_volatility == pytest.approx(optim.vol(weights, covariance))
        assert weights.sum() <= 1.5 + 1e-9
    with pytest.raises(ValueError, match="asset-class caps"):
        reoptimize_for_client("erc", covariance, RISK_BANDS[0], max_etf_weight=.35,
                              allow_borrowing=False, class_weight_caps={"unknown": .25})


def test_fixed_benchmark_class_cap_scales_with_cash_and_keeps_the_risky_mix():
    assets = ["SPY", "IEF"]
    covariance = pd.DataFrame(np.diag([.04, .01]), index=assets, columns=assets)
    fit = reoptimize_for_client("benchmark_60_40", covariance, RISK_BANDS[-1],
                               max_etf_weight=1., allow_borrowing=True,
                               class_weight_caps={"equity": .3}).allocation
    assert fit.risky_weights.to_dict() == pytest.approx({"SPY": .3, "IEF": .2})
    assert fit.cash_weight == pytest.approx(.5)


def test_band_range_boundary_contract():
    conservative, balanced, _, aggressive = RISK_BANDS
    assert volatility_band_position(.06, conservative) == "above"
    assert volatility_band_position(.06, balanced) == "within"
    assert volatility_band_position(.05, balanced) == "below"
    assert volatility_band_position(.15, aggressive) == "within"
    with pytest.raises(ValueError, match="finite"):
        volatility_band_position(float("nan"), balanced)


def test_solver_failures_propagate_instead_of_returning_placeholder_weights(monkeypatch):
    labels = ["A", "B", "C"]
    covariance = pd.DataFrame(np.diag([.0025, .04, .09]), columns=labels, index=labels)
    positive = pd.Series(.05, index=labels)
    failure = SimpleNamespace(success=False, x=np.array([.4, .3, .3]), message="simulated solver failure")

    for module in (classic, optim, baselines):
        monkeypatch.setattr(module, "minimize", lambda *args, **kwargs: failure)
    with pytest.raises(RuntimeError, match="Classic tangency optimization failed: simulated"):
        classic.classic_weights(positive, covariance, .5)
    with pytest.raises(RuntimeError, match="capped ERC optimization failed: simulated"):
        optim.capped_erc(covariance, .5)
    with pytest.raises(RuntimeError, match="minimum-variance optimization failed: simulated"):
        classic.classic_weights(-positive, covariance, .5)


def test_invalid_weights_are_rejected_even_when_solver_reports_success(monkeypatch):
    labels = ["A", "B", "C"]
    covariance = pd.DataFrame(np.diag([.0025, .04, .09]), columns=labels, index=labels)
    positive = pd.Series(.05, index=labels)
    invalid = SimpleNamespace(success=True, x=np.array([1., 0., 0.]), message="simulated success")
    monkeypatch.setattr(classic, "minimize", lambda *args, **kwargs: invalid)
    with pytest.raises(RuntimeError, match="infeasible weights"):
        classic.classic_weights(positive, covariance, .5)
