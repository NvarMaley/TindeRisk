import numpy as np
import pandas as pd
import pytest

from src.data_loader import sentiment_polarity
from src.sector_sentiment import aggregate_company_sentiment


def company_sample():
    messages = pd.DataFrame(
        [
            ("A", "2020-01-30", 1, 0, 1),
            ("A", "2020-01-31", 9, 1, 12),
            ("B", "2020-01-31", 0, 1, 1),
            ("C", "2020-01-31", 100, 0, 100),
            ("A", "2020-02-03", 0, 0, 3),
            ("B", "2020-02-03", 2, 0, 2),
        ],
        columns=["ticker", "date", "Nbullish", "Nbearish", "N"],
    )
    messages["date"] = pd.to_datetime(messages["date"])
    messages["polarity"] = sentiment_polarity(messages)
    audit = messages[["ticker", "date"]].assign(
        gvkey=["001", "001", "002", "003", "001", "002"],
        gics_sector=["45", "45", "45", "45", "50", "45"],
        status=["mapped", "mapped", "mapped", "ambiguous_gics_sector", "mapped", "mapped"],
    )
    return messages, audit


def test_sector_polarity_pools_counts_and_uses_dated_membership():
    daily, monthly = aggregate_company_sentiment(*company_sample())
    assert daily["N"].sum() == monthly["N"].sum() == 19
    january_cutoff = daily[(daily["date"] == "2020-01-31") & (daily["gics_sector"] == "45")].iloc[0]
    assert january_cutoff["polarity"] == pytest.approx(7 / 11)
    assert january_cutoff["available_date"] == pd.Timestamp("2020-02-03")
    assert january_cutoff["companies"] == 2

    tech = monthly[monthly["gics_sector"].eq("45")].set_index("available_month")
    assert tech.loc["2020-01", "N"] == 1
    assert tech.loc["2020-02", "N"] == 15
    assert tech.loc["2020-02", "polarity"] == pytest.approx(9 / 13)
    assert tech.loc["2020-02", "companies"] == 2
    assert tech.loc["2020-02", "usable_from"] == pd.Timestamp("2020-03-02")
    neutral_only = monthly.loc[monthly["gics_sector"].eq("50")].iloc[0]
    assert neutral_only["N"] == 3
    assert np.isnan(neutral_only["polarity"])


def test_no_gics_data_produces_empty_panels():
    messages, audit = company_sample()
    daily, monthly = aggregate_company_sentiment(messages, audit.assign(status="gics_history_missing"))
    assert daily.empty and monthly.empty


def test_duplicate_assignments_fail_instead_of_multiplying_counts():
    messages, audit = company_sample()
    duplicate = pd.concat([audit, audit.iloc[[0]].assign(gics_sector="50")])
    with pytest.raises(ValueError, match="unique"):
        aggregate_company_sentiment(messages, duplicate)
