from datetime import date

import numpy as np

from riskmatch.backtesting.card_performance import card_performance


def test_dated_backtest_keeps_development_out_of_test_and_aligns_reference():
    ends = [date(2023 + i // 12, i % 12 + 1, 1) for i in range(25)]
    intervals = list(zip(ends, ends[1:]))
    returns = np.full(24, .01)
    returns[0] = -.50
    returns[-1] = -.20
    reference = np.full(24, .005)
    reference[0] = .50
    result = card_performance(returns, np.zeros(24), intervals, 9,
                              benchmark_name="equal_weight", benchmark_returns=reference)

    assert [(row["year"], row["months"]) for row in result["annual_returns"]] == [(2023, 2), (2024, 12), (2025, 1)]
    assert np.isclose(result["test"]["cumulative"], 1.01**14 * .80 - 1)
    assert result["test"]["months"] == result["reference"]["months"] == 15
    assert np.isclose(result["reference"]["cumulative"], 1.005**15 - 1)
    assert result["worst_12_months"]["start"] == "2024-01-01"
    assert result["worst_12_months"]["end"] == "2025-01-01"
    assert np.isclose(result["worst_12_months"]["return"], 1.01**11 * .80 - 1)
    assert result["development"]["months"] == 9
    assert result["replay"]["months"] == 24
