"""Date-aware identifier and industry links for the LN7 company cohort."""

from pathlib import Path

import pandas as pd

# The other six LN7 symbols (GLD, IWM, JNUG, QQQ, SPY, UVXY) are funds.
LN7_COMPANIES = ("AAPL", "AMD", "AMRN", "AMZN", "BABA", "BAC", "BB", "FB",
                 "MNKD", "NFLX", "PLUG", "TSLA", "TWTR")
LN7_START, LN7_END = "2010-01-04", "2020-03-23"
GICS_FILE = "stocktwits_gics_history.csv"
GICS_CODES = {"10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60"}
CRSP_COLUMNS = {
    "Ticker": "ticker", "PERMNO": "permno",
    "SecInfoStartDt": "effective_from", "SecInfoEndDt": "effective_through",
}
CCM_COLUMNS = {
    "LPERMNO": "permno", "gvkey": "gvkey",
    "LINKDT": "effective_from", "LINKENDDT": "effective_through",
}
GICS_COLUMNS = ["gvkey", "gics_sector", "effective_from", "effective_through", "known_from"]


def _dated_history(frame):
    history = frame.drop_duplicates().copy()
    for column in ("effective_from", "effective_through"):
        history[column] = pd.to_datetime(history[column], format="%Y-%m-%d")
    if history["effective_from"].isna().any():
        raise ValueError("Each history interval requires a start date")
    if history["effective_through"].lt(history["effective_from"]).any():
        raise ValueError("History interval ends before it begins")
    return history


def _match_history(rows, history, key, value):
    """Return a unique effective mapping or a row-level failure reason."""
    candidates = rows.loc[rows[key].notna(), ["date", key]].reset_index(names="row")
    candidates = candidates.merge(history.dropna(subset=[key, value]), on=key, how="inner")
    date = candidates["date"]
    active = candidates.loc[
        date.ge(candidates["effective_from"])
        & (candidates["effective_through"].isna() | date.le(candidates["effective_through"]))
    ]
    available = active
    if "known_from" in active:
        available = active.loc[active["date"].ge(active["known_from"])]
    matches = available[["row", value]].drop_duplicates().set_index("row")[value]
    ambiguous = matches.index[matches.index.duplicated(keep=False)]
    matched = matches.loc[~matches.index.isin(ambiguous)].reindex(rows.index)
    issue = pd.Series(f"missing_{value}", index=rows.index, dtype="string")
    issue.loc[issue.index.isin(active["row"])] = f"unavailable_{value}"
    issue.loc[issue.index.isin(ambiguous)] = f"ambiguous_{value}"
    issue.loc[matched.notna()] = pd.NA
    return matched, issue


def _link_company_identifiers(days, security_history, company_links):
    result = days[["ticker", "date"]].reset_index(drop=True)
    result["date"] = pd.to_datetime(result["date"], utc=True).dt.tz_localize(None).dt.normalize()
    if result.isna().any().any() or result.duplicated().any():
        raise ValueError("Company days require nonmissing, unique ticker/calendar-date keys")
    result["permno"], result["status"] = _match_history(
        result, _dated_history(security_history), "ticker", "permno"
    )
    result["gvkey"], company_issue = _match_history(
        result, _dated_history(company_links), "permno", "gvkey"
    )
    result["status"] = result["status"].fillna(company_issue)
    return result


def link_company_days(days, security_history, company_links, gics_history=None):
    """Link each observation without using ticker or GICS values from later dates."""
    result = _link_company_identifiers(days, security_history, company_links)
    if gics_history is None:
        result["gics_sector"] = pd.Series(pd.NA, index=result.index, dtype="string")
        result["status"] = result["status"].fillna("gics_history_missing")
        return result

    gics = _dated_history(gics_history[GICS_COLUMNS])
    gics["known_from"] = pd.to_datetime(gics["known_from"], format="%Y-%m-%d")
    if gics[["gvkey", "known_from"]].isna().any().any() or not gics["gics_sector"].isin(GICS_CODES).all():
        raise ValueError("GICS history requires a GVKEY, documented known-from date and valid sector code")
    result["gics_sector"], gics_issue = _match_history(result, gics, "gvkey", "gics_sector")
    result["status"] = result["status"].fillna(gics_issue).fillna("mapped")
    return result


def _load_ln7_links(wrds_dir: Path, *, include_icb: bool = False):
    columns = {**CRSP_COLUMNS, **({"ICBIndustry": "icb_industry"} if include_icb else {})}
    security_chunks = pd.read_csv(
        wrds_dir / "crsp_msf.csv", usecols=columns, dtype="string", chunksize=250_000,
    )
    securities = pd.concat([
        chunk.loc[chunk["Ticker"].isin(LN7_COMPANIES)].drop_duplicates()
        for chunk in security_chunks
    ], ignore_index=True).rename(columns=columns)
    links = pd.read_csv(
        wrds_dir / "ccm_lnkhist.csv", usecols=[*CCM_COLUMNS, "LINKPRIM", "LINKTYPE"],
        dtype="string", na_values={"LINKENDDT": ["E"]},
    )
    primary = links["LINKPRIM"].isin(["P", "C"]) & links["LINKTYPE"].isin(["LC", "LU", "LS"])
    links = links.loc[primary & links["LPERMNO"].isin(securities["permno"]), list(CCM_COLUMNS)]
    return securities, links.rename(columns=CCM_COLUMNS)


def audit_ln7_companies(days, wrds_dir: Path, gics_path: Path):
    """Read local WRDS extracts in chunks and return the GICS join audit."""
    securities, links = _load_ln7_links(wrds_dir)
    gics = pd.read_csv(gics_path, dtype="string", usecols=GICS_COLUMNS) if gics_path.is_file() else None
    return link_company_days(days, securities, links, gics)


def audit_ln7_icb(days, wrds_dir: Path):
    """Use effective CRSP ICB intervals for an exploratory classification."""
    securities, links = _load_ln7_links(wrds_dir, include_icb=True)
    result = _link_company_identifiers(days, securities, links)
    securities["icb_industry"] = securities["icb_industry"].replace("NOAVAIL", pd.NA)
    result["icb_industry"], issue = _match_history(
        result, _dated_history(securities), "permno", "icb_industry"
    )
    result["status"] = result["status"].fillna(issue).fillna("mapped")
    result.loc[result["status"].ne("mapped"), "icb_industry"] = pd.NA
    return result
