import numpy as np
import pandas as pd
import pytest

from src.build_diagnostics import subperiod_diagnostics


def test_blocks_partition_the_sample_and_report_clipped_coverage():
    dates = pd.bdate_range("2019-12-11", "2020-01-08")
    returns = pd.DataFrame({"SPY": np.linspace(-.02, .02, len(dates))}, index=dates)
    cash = pd.Series(0., index=dates)
    result = subperiod_diagnostics(returns, cash).set_index("subperiod")
    before = result.loc["Through 2019"]
    short = result.loc["2020–2021"]
    assert before.last_session == pd.Timestamp("2019-12-31")
    assert short.first_session == pd.Timestamp("2020-01-01")
    assert short.last_session == dates[-1]
    assert before.sessions + short.sessions == result.loc["Full sample", "sessions"]
    assert pd.isna(short.JB_pvalue)
    assert pd.isna(short.tail_sessions)
    assert before.ES95_daily == pytest.approx(-.02)
    assert before.tail_sessions == 1
    with pytest.raises(ValueError, match="dates"):
        subperiod_diagnostics(returns, cash.iloc[1:])
