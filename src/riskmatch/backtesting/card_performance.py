"""Dated performance breakdowns for strategy cards."""
from itertools import groupby

import numpy as np

from riskmatch.backtesting.baselines import metrics


def _period(returns, cash, intervals):
    summary = metrics(returns, cash)
    return {
        "start": str(intervals[0][0]), "end": str(intervals[-1][1]), "months": len(returns),
        "cumulative": summary["cumulative"], "cagr": summary["cagr"],
        "vol": summary["annual_volatility"], "drawdown": summary["max_drawdown"],
    }


def _annual_returns(returns, intervals):
    by_year = []
    for year, group in groupby(range(len(returns)), key=lambda i: intervals[i][1].year):
        months = list(group)
        by_year.append({"year": year, "months": len(months),
                        "return": float(np.prod(1 + returns[months]) - 1)})
    return by_year


def card_performance(returns, cash, intervals, split, *, benchmark_name=None, benchmark_returns=None):
    """Compare only aligned monthly observations from the same evaluation period."""
    test = returns[split:]
    dates = intervals[split:]
    worst_year = None
    if len(test) >= 12:
        windows = np.lib.stride_tricks.sliding_window_view(test, 12)
        results = np.prod(1 + windows, axis=1) - 1
        worst = int(np.argmin(results))
        worst_year = {"start": str(dates[worst][0]), "end": str(dates[worst + 11][1]),
                      "return": float(results[worst])}
    reference = None
    if benchmark_returns is not None:
        reference = _period(benchmark_returns[split:], cash[split:], dates)
        reference["name"] = benchmark_name
    return {
        "test": _period(test, cash[split:], dates),
        "development": _period(returns[:split], cash[:split], intervals[:split]) if split >= 2 else None,
        "replay": _period(returns, cash, intervals),
        "annual_returns": _annual_returns(test, dates),
        "development_annual_returns": _annual_returns(returns[:split], intervals[:split]),
        "worst_12_months": worst_year, "reference": reference,
    }
