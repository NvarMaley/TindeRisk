"""Company-derived industry sentiment for the Step 4.1d research hypothesis."""

import pandas as pd

from .data_loader import next_market_session, sentiment_polarity, validate_sentiment_firm_daily
from .historical_gics import GICS_CODES

COUNTS = ["Nbullish", "Nbearish", "N"]


def _pool_counts(rows, keys):
    grouped = rows.groupby(keys, as_index=False, observed=True).agg(
        **{column: (column, "sum") for column in COUNTS},
        companies=("gvkey", "nunique"),
    )
    grouped["labelled"] = grouped["Nbullish"] + grouped["Nbearish"]
    grouped["polarity"] = sentiment_polarity(grouped)
    return grouped


def aggregate_company_sentiment(
    sentiment: pd.DataFrame, company_days: pd.DataFrame, *, sector_column: str = "gics_sector",
):
    """Return daily and monthly sector panels built from validated ticker-day links."""
    validate_sentiment_firm_daily(sentiment)
    keys = ["ticker", "date"]
    if company_days[keys].isna().any().any() or company_days.duplicated(keys).any():
        raise ValueError("Company link audit requires unique, nonmissing ticker/date keys")
    if sector_column not in {"gics_sector", "icb_industry"}:
        raise ValueError("Expected a GICS sector or ICB industry classification")
    mapped = company_days.loc[company_days["status"].eq("mapped"), [*keys, "gvkey", sector_column]]
    valid_sector = (mapped[sector_column].isin(GICS_CODES) if sector_column == "gics_sector"
                    else mapped[sector_column].notna() & mapped[sector_column].ne("NOAVAIL"))
    if mapped["gvkey"].isna().any() or not valid_sector.all():
        raise ValueError("Mapped company days require a GVKEY and valid industry classification")
    joined = sentiment[[*keys, *COUNTS]].merge(mapped, on=keys, validate="one_to_one")
    joined["available_date"] = next_market_session(joined["date"])
    joined["available_month"] = joined["available_date"].dt.to_period("M")

    daily = _pool_counts(joined, [sector_column, "date", "available_date"])
    monthly = _pool_counts(joined, [sector_column, "available_month"])
    month_end = monthly["available_month"].dt.to_timestamp(how="end").dt.normalize()
    monthly["usable_from"] = next_market_session(month_end)
    return daily, monthly
