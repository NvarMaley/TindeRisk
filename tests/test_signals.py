import numpy as np
import pandas as pd
import pytest

from src.signals import sentiment_view_matrix


ASSETS = ["IEF", "XLF", "XLE", "XLK", "TLT"]
SECTORS = ["XLE", "XLK", "XLF"]
SCORES = pd.Series({"XLF": -.2, "XLE": .4, "XLK": .1, "TLT": 2, "SPY": -2})
DATES = dict(usable_from="2020-03-02", usable_through="2020-03-31")


def test_relative_view_is_aligned_and_spreads_only_eligible_sectors():
    view = sentiment_view_matrix(ASSETS, SECTORS, "2020-03-02", scores=SCORES, validated=True, **DATES)
    assert view.columns.tolist() == ASSETS
    assert view.index.tolist() == ["stocktwits_sector_spread"]
    assert view.iloc[0].tolist() == [0., -1., 1., 0., 0.]
    assert view.sum(axis=1).item() == 0
    example_expected_returns = pd.Series({"IEF": .01, "XLF": .02, "XLE": .06, "XLK": .05, "TLT": .03})
    assert (view @ example_expected_returns).item() == pytest.approx(.04)


def test_no_validated_view_keeps_a_zero_row_matrix_with_the_full_universe():
    view = sentiment_view_matrix(ASSETS, SECTORS, "2020-03-02", scores=SCORES, **DATES)
    assert view.shape == (0, len(ASSETS))
    assert view.columns.tolist() == ASSETS


@pytest.mark.parametrize("date", ["2020-02-28", "2020-04-01"])
def test_future_or_stale_signal_is_ineligible(date):
    view = sentiment_view_matrix(ASSETS, SECTORS, date, scores=SCORES, validated=True, **DATES)
    assert view.empty


@pytest.mark.parametrize("scores", [
    {"XLE": .4, "XLK": .4, "XLF": -.2},
    {"XLE": .4, "XLK": np.nan, "XLF": np.inf},
    {"XLE": .4, "XLK": .4},
])
def test_ties_or_insufficient_finite_sector_scores_give_no_view(scores):
    view = sentiment_view_matrix(ASSETS, SECTORS, "2020-03-31", scores=pd.Series(scores),
                                 validated=True, **DATES)
    assert view.empty


def test_invalid_universe_or_missing_provenance_dates_raise():
    with pytest.raises(ValueError, match="unique subset"):
        sentiment_view_matrix(ASSETS, ["SPY"], "2020-03-02")
    with pytest.raises(ValueError, match="validity dates"):
        sentiment_view_matrix(ASSETS, SECTORS, "2020-03-02", scores=SCORES, validated=True)
