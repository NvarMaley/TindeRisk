"""Compare covariance estimators on the same constrained GMV problem."""

import numpy as np
import pandas as pd

from .baselines import apply_monthly_targets, minimum_variance_weights
from .estimation import ledoit_wolf_constant_corr, sample_cov, validate_returns


def compare_covariances(history: pd.DataFrame, returns: pd.DataFrame,
                        closes: pd.DatetimeIndex, final_month_close: pd.Timestamp,
                        window: int, max_weight: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimate at each close and measure only subsequent holding returns.

    The first target initializes the portfolio and its turnover is undefined.
    The final holding period is scored only if its month-end close is present.
    """
    validate_returns(history)
    if (history.index.get_indexer(returns.index) < 0).any() or not history.loc[returns.index].equals(returns):
        raise ValueError("evaluation returns must match their history")
    if window < 2:
        raise ValueError("window must contain at least two sessions")
    if (returns.empty or not len(closes) or closes[-1] >= final_month_close
            or returns.index[-1] > final_month_close):
        raise ValueError("invalid evaluation sample or final scheduled month-end")
    stop_dates = closes[1:].append(pd.DatetimeIndex([final_month_close]))
    records, allocations = [], {}
    for estimator in ("sample", "lw_constcorr"):
        estimates, targets = [], []
        for close in closes:
            trailing = history.loc[:close].tail(window)
            if len(trailing) != window or trailing.index[-1] != close:
                raise ValueError(f"missing trailing window at {close.date()}")
            covariance = (sample_cov(trailing) if estimator == "sample"
                          else ledoit_wolf_constant_corr(trailing)[0])
            weight = minimum_variance_weights(covariance, max_weight)
            targets.append(weight)
            estimates.append((np.linalg.cond(covariance), float(np.sqrt(weight @ covariance @ weight))))

        target_table = pd.DataFrame(targets, index=closes)
        daily = apply_monthly_targets(returns, target_table)["gross_return"]
        allocations[estimator] = target_table
        pretrade = None
        for close, stop, weight, (condition, prediction) in zip(
                closes, stop_dates, targets, estimates, strict=True):
            hold = returns.loc[(returns.index > close) & (returns.index <= stop)]
            if hold.empty:
                raise ValueError(f"no holding returns after {close.date()}")
            complete = hold.index[-1] == stop
            score = daily.loc[hold.index].std(ddof=1) * np.sqrt(252) if complete else np.nan
            records.append({"estimator": estimator, "decision_close": close,
                            "first_session": hold.index[0], "last_session": hold.index[-1],
                            "complete_month": complete, "sessions": len(hold),
                            "condition_number": condition, "predicted_vol": prediction,
                            "realized_vol": score, "vol_error": prediction - score,
                            "turnover_two_way": (weight - pretrade).abs().sum() if pretrade is not None else np.nan})
            grown = weight * (1 + hold).prod(axis=0)
            pretrade = grown / grown.sum()
    rows = pd.DataFrame(records).set_index(["estimator", "decision_close"])
    weights = pd.concat(allocations, names=["estimator", "decision_close"])
    return rows, weights
