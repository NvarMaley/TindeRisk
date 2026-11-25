import numpy as np
import pytest
from riskmatch.analytics.cash_reference import benchmark


def test_lagged_cash_reference():
    cash=np.arange(120)/10000
    dates=list(range(120))
    r=cash+.001
    result=benchmark(r,dates,cash)
    assert result["test_count"]==20
    assert result["excess_mean"]==pytest.approx(.001)
    for day,actual,prediction,realized in result["history"]:
        assert prediction==pytest.approx(cash[int(day)-1])
        assert realized==pytest.approx(cash[int(day)])
    with pytest.raises(ValueError):
        benchmark(r,dates,cash[:-1])
