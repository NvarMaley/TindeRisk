import numpy as np
import pandas as pd
import pytest

from src.macro_regimes import macro_month_ends, select_macro_hmm


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
