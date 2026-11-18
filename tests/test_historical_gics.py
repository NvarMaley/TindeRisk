import pandas as pd
import pytest

from src.historical_gics import link_company_days


def frame(fields, rows):
    return pd.DataFrame(rows, columns=fields.split(), dtype="string")


SECURITY = "ticker permno effective_from effective_through"
LINK = "permno gvkey effective_from effective_through"
CLASSIFICATION = "gvkey gics_sector effective_from effective_through known_from"


def test_reused_ticker_respects_both_link_intervals_and_classification_availability():
    days = frame("ticker date", [
        ("ABC", "2018-09-21"), ("ABC", "2018-09-22"), ("ABC", "2018-09-23"),
        ("ABC", "2018-09-24"), ("ABC", "2018-09-25"), ("ZZZ", "2018-09-25"),
    ])
    securities = frame(SECURITY, [
        ("ABC", "10", "2018-01-01", "2018-09-21"),
        ("ABC", "20", "2018-09-22", None),
    ])
    links = frame(LINK, [
        ("10", "000010", "2018-01-01", "2018-09-21"),
        ("20", "000020", "2018-09-23", None),
    ])
    gics = frame(CLASSIFICATION, [
        ("000010", "45", "2018-01-01", None, "2018-01-01"),
        ("000020", "50", "2018-09-23", None, "2018-09-24"),
    ])
    result = link_company_days(days, securities, links, gics)
    assert result["status"].tolist() == [
        "mapped", "missing_gvkey", "unavailable_gics_sector", "mapped", "mapped", "missing_permno",
    ]
    assert result["gics_sector"].dropna().tolist() == ["45", "50", "50"]
    assert result["gvkey"].dropna().tolist() == ["000010", "000020", "000020", "000020"]


def test_overlapping_security_and_sector_candidates_are_left_unclassified():
    days = frame("ticker date", [("ABC", "2020-01-02"), ("DEF", "2020-01-02")])
    securities = frame(SECURITY, [
        ("ABC", "10", "2019-01-01", None), ("ABC", "20", "2019-01-01", None),
        ("DEF", "30", "2019-01-01", None), ("DEF", "30", "2019-01-01", None),
    ])
    links = frame(LINK, [("30", "000030", "2019-01-01", None)])
    gics = frame(CLASSIFICATION, [
        ("000030", "45", "2019-01-01", None, "2019-01-01"),
        ("000030", "50", "2020-01-01", None, "2020-01-01"),
    ])
    result = link_company_days(days, securities, links, gics)
    assert result["status"].tolist() == ["ambiguous_permno", "ambiguous_gics_sector"]
    assert result["gics_sector"].isna().all()


def test_absent_history_and_unknown_availability_are_distinct():
    days = frame("ticker date", [("ABC", "2020-01-02")])
    securities = frame(SECURITY, [("ABC", "10", "2019-01-01", None)])
    links = frame(LINK, [("10", "000010", "2019-01-01", None)])
    gics = frame(CLASSIFICATION, [("000010", "45", "2019-01-01", None, None)])
    assert link_company_days(days, securities, links)["status"].item() == "gics_history_missing"
    with pytest.raises(ValueError, match="known-from"):
        link_company_days(days, securities, links, gics)


def test_local_extract_supports_the_ccm_open_end_marker(tmp_path):
    from src.historical_gics import audit_ln7_companies

    (tmp_path / "crsp_msf.csv").write_text(
        "Ticker,PERMNO,SecInfoStartDt,SecInfoEndDt\nAAPL,12345,2010-01-04,\n"
    )
    (tmp_path / "ccm_lnkhist.csv").write_text(
        "LPERMNO,gvkey,LINKDT,LINKENDDT,LINKPRIM,LINKTYPE\n12345,000123,2010-01-04,E,P,LC\n"
        "12345,000321,2010-01-04,E,N,LC\n"
    )
    gics = tmp_path / "history.csv"
    gics.write_text(
        "gvkey,gics_sector,effective_from,effective_through,known_from\n"
        "000123,45,2010-01-04,,2010-01-04\n"
    )
    days = frame("ticker date", [("AAPL", "2018-01-02")])
    result = audit_ln7_companies(days, tmp_path, gics)
    assert result.loc[0, ["gvkey", "gics_sector", "status"]].tolist() == ["000123", "45", "mapped"]
