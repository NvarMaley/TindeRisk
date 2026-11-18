import pandas as pd
import pytest

from src.provenance import observation_records


def test_observation_identity_survives_publication_lag():
    series = pd.Series([2.5], index=pd.to_datetime(["2020-01-01"]), name="CPI")
    result = observation_records(
        series, available_dates=pd.to_datetime(["2020-02-29"]),
        source="FRED", downloaded_at_utc="2026-11-18T12:00:00Z",
        availability_rule="conservative monthly lag; latest vintage",
    )
    assert result.iloc[0].observation_date == pd.Timestamp("2020-01-01")
    assert result.iloc[0].available_date == pd.Timestamp("2020-02-29")
    assert str(result.downloaded_at_utc.dtype) == "datetime64[ns, UTC]"


def test_unknown_download_is_not_fabricated():
    series = pd.Series([1.], index=pd.to_datetime(["2020-01-01"]), name="sentiment")
    result = observation_records(series, available_dates=series.index,
                                 source="professor", downloaded_at_utc=None,
                                 availability_rule="assumed")
    assert result.downloaded_at_utc.isna().all()
    assert result.download_status.iloc[0] == "unknown_original_download"
    with pytest.raises(ValueError, match="precede"):
        observation_records(series, available_dates=pd.to_datetime(["2019-12-31"]),
                            source="professor", downloaded_at_utc=None, availability_rule="invalid")
