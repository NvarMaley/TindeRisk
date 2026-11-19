"""Evaluate an exploratory StockTwits high-minus-low sector spread."""

import numpy as np
import pandas as pd

from .signal_validation import monthly_holding_returns

# Restrict the historical comparison to the nine configured sector proxies.
GICS_SECTOR_ETFS = {
    "10": "XLE", "15": "XLB", "20": "XLI", "25": "XLY", "30": "XLP",
    "35": "XLV", "40": "XLF", "45": "XLK", "55": "XLU",
}


def high_low_spread(monthly, prices, *, before_month):
    """Rank observed scores before joining returns and retain unpriced selections."""
    cutoff = pd.Period(before_month, freq="M")
    if pd.isna(cutoff):
        raise ValueError("The validation requires an exclusive holding-month cutoff")
    if monthly.duplicated(["available_month", "asset"]).any():
        raise ValueError("Monthly polarity must be unique by asset and month")
    scores = monthly.loc[
        monthly["asset"].isin(prices.columns) & (monthly["available_month"] + 1).lt(cutoff)
    ]
    selected = []
    for month, rows in scores.groupby("available_month", sort=True):
        values = rows.set_index("asset")["polarity"].astype(float)
        observed = values[np.isfinite(values)]
        status = "insufficient_sectors"
        high = low = None
        if len(observed) >= 2:
            highest = observed.loc[observed.eq(observed.max())]
            lowest = observed.loc[observed.eq(observed.min())]
            status = "tied_extremes"
            if len(highest) == len(lowest) == 1:
                high, low = highest.index[0], lowest.index[0]
                status = "unpriced"
        selected.append((month + 1, len(observed), high, low, status))
    result = pd.DataFrame(selected, columns=[
        "target_month", "covered_sectors", "high_asset", "low_asset", "status",
    ]).set_index("target_month")
    result.index = pd.PeriodIndex(result.index, freq="M", name="target_month")
    result["spread"] = np.nan
    historical_prices = prices.loc[prices.index < cutoff.start_time]
    if not result.empty and not historical_prices.empty:
        returns = monthly_holding_returns(historical_prices).reindex(result.index)
        for month, row in result.loc[result["status"].eq("unpriced")].iterrows():
            spread = returns.loc[month, row["high_asset"]] - returns.loc[month, row["low_asset"]]
            if pd.notna(spread):
                result.loc[month, ["status", "spread"]] = ["priced", spread]
    return result


def spread_summary(outcomes, validation_start):
    """Report coverage and realized spread separately in training and validation."""
    boundary = pd.Period(validation_start, freq="M")
    if pd.isna(boundary):
        raise ValueError("A chronological validation boundary is required")
    masks = {"train": outcomes.index < boundary, "validation": outcomes.index >= boundary}
    summary = {}
    for label, mask in masks.items():
        rows = outcomes.loc[mask]
        spreads = rows["spread"].dropna()
        summary[label] = {
            "signal_months": len(rows), "priced_months": len(spreads),
            "mean_spread": spreads.mean(), "positive_months": int(spreads.gt(0).sum()),
        }
    return pd.DataFrame.from_dict(summary, orient="index").rename_axis("window")
