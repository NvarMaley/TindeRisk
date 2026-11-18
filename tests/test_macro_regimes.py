from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from src.macro_regimes import (
    expanding_regime_probabilities, filtered_state_probabilities, macro_month_ends,
    select_macro_hmm,
)


def test_month_end_sampling_uses_nyse_endpoints_and_excludes_partial_month():
    panel = pd.DataFrame({"macro": [1., 2., 99., 3.]}, index=pd.to_datetime(
        ["2020-01-31", "2020-02-28", "2020-03-20", "2020-03-31"]
    ))
    months = macro_month_ends(panel, "2020-01-01", "2020-03-20")
    assert months.index.tolist() == [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-28")]
    assert months["macro"].tolist() == [1., 2.]
    with pytest.raises(ValueError, match="complete macro observations"):
        macro_month_ends(panel.iloc[[0, 2, 3]], "2020-01-01", "2020-03-20")


def test_bic_compares_candidates_on_the_same_standardized_training_history():
    rng = np.random.default_rng(391)
    states = np.tile(np.repeat([-3., 3.], 12), 5)
    months = pd.date_range("2010-01-31", periods=len(states), freq="ME")
    data = pd.DataFrame({"A": states + rng.normal(0, .25, len(months)),
                         "B": -states + rng.normal(0, .4, len(months))}, index=months)
    model, scaler, report = select_macro_hmm(data, candidates=(2, 3), seeds=(0, 4, 9))
    assert model.n_components == report["bic"].idxmin() == 2
    assert report.loc[2, "bic"] == pytest.approx(model.bic(scaler.transform(data)))
    assert report["months"].tolist() == [120, 120]
    assert report["total_starts"].tolist() == [3, 3]
    np.testing.assert_allclose(scaler.mean_, data.mean())


def test_hmm_rejects_monthly_gaps_instead_of_compressing_time():
    index = pd.date_range("2010-01-31", periods=20, freq="ME").delete(5)
    data = pd.DataFrame({"A": np.arange(len(index), dtype=float)}, index=index)
    with pytest.raises(ValueError, match="consecutive months"):
        select_macro_hmm(data)


def test_forward_filter_agrees_with_a_hand_calculation_and_does_not_use_future():
    model = GaussianHMM(n_components=2, covariance_type="diag")
    model.n_features = 1
    model.startprob_ = np.array([.6, .4])
    model.transmat_ = np.array([[.8, .2], [.3, .7]])
    model.means_ = np.array([[-1.], [1.]])
    model.covars_ = np.array([[1.], [1.]])
    observations = np.array([[0.3], [1.2], [-0.6]])
    p0 = model.startprob_ * norm.pdf(.3, loc=[-1., 1.])
    p0 /= p0.sum()
    p1 = (p0 @ model.transmat_) * norm.pdf(1.2, loc=[-1., 1.])
    p1 /= p1.sum()
    short = filtered_state_probabilities(model, observations[:2])
    np.testing.assert_allclose(short, [p0, p1])
    np.testing.assert_allclose(filtered_state_probabilities(model, observations)[:2], short)


def test_expanding_probabilities_refit_only_on_prior_months():
    dates = pd.date_range("2010-01-31", periods=40, freq="BME")
    rng = np.random.default_rng(2841)
    means = np.tile(np.repeat([-1., 1.], 5), 4)
    panel = pd.DataFrame({"A": means + rng.normal(0, .18, len(dates))}, index=dates)
    options = dict(first_observation=dates[-3], states=2, seeds=(0, 1, 2))
    result = expanding_regime_probabilities(panel, **options)
    modified = panel.copy()
    modified.iloc[-1] = 100
    alternate = expanding_regime_probabilities(modified, **options)

    pd.testing.assert_frame_equal(result.iloc[:-1], alternate.iloc[:-1])
    assert result["train_months"].tolist() == [37, 38, 39]
    assert (result["train_through"] < result.index).all()
    assert (result["available_date"] > result.index).all()
    np.testing.assert_allclose(result[["state_0", "state_1"]].sum(axis=1), 1)


def test_expanding_filter_keeps_state_identifiers_when_a_refit_swaps_them(monkeypatch):
    from types import SimpleNamespace

    import src.macro_regimes as regimes

    dates = pd.date_range("2010-01-31", periods=14, freq="ME")
    panel = pd.DataFrame({"A": np.ones(14)}, index=dates)
    models = iter((
        SimpleNamespace(means_=np.array([[-1.], [1.]])),
        SimpleNamespace(means_=np.array([[1.], [-1.]])),
    ))
    scaler = SimpleNamespace(
        mean_=np.array([0.]), scale_=np.array([1.]),
        transform=np.asarray, inverse_transform=np.asarray,
    )

    def fit(*args, **kwargs):
        return next(models), scaler, pd.DataFrame({"converged_starts": [1]}, index=[2])

    def filter_for_fixture(model, observations):
        return np.tile(np.where(model.means_[:, 0] > 0, .8, .2), (len(observations), 1))

    monkeypatch.setattr(regimes, "select_macro_hmm", fit)
    monkeypatch.setattr(regimes, "filtered_state_probabilities", filter_for_fixture)
    result = expanding_regime_probabilities(panel, first_observation=dates[-2], states=2)
    np.testing.assert_allclose(result[["state_0", "state_1"]], [[.2, .8], [.2, .8]])
