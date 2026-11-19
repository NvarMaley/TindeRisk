"""Chronological StockTwits signal checks for Step 4.1e."""

from itertools import combinations

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import statsmodels.api as sm
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

from .data_loader import sentiment_polarity


def monthly_tag_polarity(asset_daily):
    """Pool provisional direct-ETF mentions in their NYSE availability month."""
    months = asset_daily["available_date"].dt.to_period("M")
    pooled = (asset_daily.assign(available_month=months)
              .groupby(["asset", "available_month"], as_index=False)[["Nbullish", "Nbearish"]].sum())
    return pooled.assign(polarity=sentiment_polarity(pooled))


def monthly_holding_returns(prices):
    """Return each scheduled month's first-close to last-close asset returns."""
    if prices.empty:
        raise ValueError("Adjusted closes are required for forward returns")
    start = prices.index.min().to_period("M").start_time
    end = prices.index.max().to_period("M").end_time.normalize()
    sessions = mcal.get_calendar("NYSE").valid_days(start, end, tz=None)
    endpoints = sessions.to_series().groupby(sessions.to_period("M")).agg(["first", "last"])
    opening = prices.reindex(endpoints["first"]).set_axis(endpoints.index)
    closing = prices.reindex(endpoints["last"]).set_axis(endpoints.index)
    valid = opening.gt(0) & closing.gt(0) & np.isfinite(opening) & np.isfinite(closing)
    return (closing / opening - 1).where(valid).rename_axis(index="target_month")


def matched_forward_returns(monthly, prices, benchmark):
    """Pair month t polarity with month t+1 close-to-close relative returns."""
    realized = monthly_holding_returns(prices)
    relative = (realized.sub(realized[benchmark], axis="index").drop(columns=benchmark)
                .rename_axis(index="target_month", columns="asset").stack()
                .rename("relative_return").reset_index())
    feature = monthly.assign(target_month=monthly["available_month"] + 1)
    return feature.merge(relative, on=["asset", "target_month"], validate="one_to_one")


def _rank_comparison(first, second):
    if min(len(first), len(second)) < 5:
        return np.nan, np.nan
    if first.nunique() == second.nunique() == 1 and first.iloc[0] == second.iloc[0]:
        return 0.0, 1.0
    result = mannwhitneyu(first, second, alternative="two-sided", method="asymptotic")
    return 2 * result.statistic / (len(first) * len(second)) - 1, result.pvalue


def _holm(table):
    table["holm_p"] = np.nan
    valid = table["nominal_p"].notna()
    if valid.any():
        table.loc[valid, "holm_p"] = multipletests(table.loc[valid, "nominal_p"], method="holm")[1]
    return table


def _huber(rows):
    x = sm.add_constant(rows[["polarity"]], has_constant="add")
    fit = sm.RLM(rows["relative_return"], x, M=sm.robust.norms.HuberT()).fit(maxiter=200)
    if fit.fit_history["iteration"] >= 200:
        raise RuntimeError("Huber regression did not converge")
    return fit.params


def validate_predictor(pairs, validation_start, end):
    """Learn each ETF's cutoff and model on train only, then score the next window."""
    validation_start, end = (pd.Period(value, freq="M") for value in (validation_start, end))
    if validation_start > end:
        raise ValueError("Validation start must be no later than its end")
    observed = pairs.loc[pairs["target_month"].le(end)].dropna(subset=["polarity", "relative_return"])
    rows = []
    for asset, asset_rows in observed.groupby("asset", sort=True):
        train = asset_rows.loc[asset_rows["target_month"].lt(validation_start)]
        validation = asset_rows.loc[asset_rows["target_month"].ge(validation_start)]
        row = {"asset": asset, "train_months": len(train), "validation_months": len(validation),
               "high_months": 0, "low_months": 0, "rank_effect": np.nan, "nominal_p": np.nan,
               "train_slope": np.nan, "validation_slope": np.nan,
               "huber_mae": np.nan, "mean_mae": np.nan}
        if len(train) >= 24 and len(validation) >= 12 and train["polarity"].nunique() > 1:
            cutoff = train["polarity"].median()
            high = validation.loc[validation["polarity"].gt(cutoff), "relative_return"]
            low = validation.loc[validation["polarity"].lt(cutoff), "relative_return"]
            rank_effect, pvalue = _rank_comparison(high, low)
            fit = _huber(train)
            predictions = fit["const"] + fit["polarity"] * validation["polarity"]
            actual = validation["relative_return"]
            row.update(
                high_months=len(high), low_months=len(low), rank_effect=rank_effect, nominal_p=pvalue,
                train_slope=fit["polarity"], huber_mae=(predictions - actual).abs().mean(),
                mean_mae=(train["relative_return"].mean() - actual).abs().mean(),
            )
            if validation["polarity"].nunique() > 1:
                row["validation_slope"] = _huber(validation)["polarity"]
        rows.append(row)
    table = pd.DataFrame(rows)
    return _holm(table) if not table.empty else table


def ln7_event_rank_tests(paths):
    """Compare CAR and CAP between event types at the three LN7 horizons."""
    rows = []
    for horizon in (-5, 0, 5):
        day = paths.loc[paths["relative_session"].eq(horizon)]
        for measure in ("CAR", "CAP"):
            for first, second in combinations(("Good", "Neutral", "Bad"), 2):
                a = day.loc[day["event_type"].eq(first), measure].dropna()
                b = day.loc[day["event_type"].eq(second), measure].dropna()
                effect, pvalue = _rank_comparison(a, b)
                rows.append({"session": horizon, "measure": measure, "first": first, "second": second,
                             "n_first": len(a), "n_second": len(b), "rank_effect": effect, "nominal_p": pvalue})
    return _holm(pd.DataFrame(rows))
