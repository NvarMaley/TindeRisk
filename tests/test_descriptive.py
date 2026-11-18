import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.descriptive import descriptive_statistics, max_drawdown


def test_initial_loss_counts_toward_drawdown():
    assert max_drawdown(pd.Series([-.2, .1])) == pytest.approx(-.2)
    assert max_drawdown(pd.Series([.1, -.5, .1])) == pytest.approx(-.5)
    assert max_drawdown(pd.Series([.1, .1])) == 0


def test_statistics_match_independent_formulae_and_raf_conventions():
    r = pd.Series([.01, -.02, .03, -.01, .02, -.03]*3, index=pd.bdate_range("2020-01-01", periods=18))
    rf = pd.Series(.0001, index=r.index)
    row = descriptive_statistics(r.to_frame("ETF"), rf).loc["ETF"]
    assert row.ann_return == pytest.approx((1+r).prod()**(252/len(r))-1)
    assert row.ann_vol == pytest.approx(np.std(r, ddof=1)*np.sqrt(252))
    assert row.sharpe == pytest.approx(np.mean(r-.0001)/np.std(r, ddof=1)*np.sqrt(252))
    assert row["skew"] == pytest.approx(stats.skew(r))
    assert row.ex_kurtosis == pytest.approx(stats.kurtosis(r))
    assert row.VaR95_daily == pytest.approx(-.03)
    assert row.ES95_daily == pytest.approx(-.03)


def test_constant_series_has_no_infinite_sharpe():
    r = pd.DataFrame({"cash": [0.]*15}, index=pd.bdate_range("2020-01-01", periods=15))
    result = descriptive_statistics(r, pd.Series(0., index=r.index))
    assert np.isnan(result.loc["cash", "sharpe"])
    assert result.loc["cash", "max_drawdown"] == 0


def test_misaligned_and_missing_inputs_fail():
    r = pd.DataFrame({"ETF": [.01]*15}, index=pd.bdate_range("2020-01-01", periods=15))
    rf = pd.Series(0., index=r.index)
    with pytest.raises(ValueError, match="match"):
        descriptive_statistics(r, rf.iloc[1:])
    r.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        descriptive_statistics(r, rf)
