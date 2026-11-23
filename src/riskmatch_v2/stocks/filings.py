"""Link timestamped EDGAR filing versions conservatively to dated equity identities."""

import re
from datetime import date

import numpy as np
import pandas as pd
import requests

from ..equity_extension.fetch import CAT
from ..library.sources import checked
from ..universe.data import BR
from .audit import LOCAL, records


def issuer(name):
    text = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper().replace("&", " AND "))
    words = text.split()
    while words and words[-1] in {
        "INC",
        "INCORPORATED",
        "CORP",
        "CORPORATION",
        "LTD",
        "CO",
        "COMPANY",
    }:
        words.pop()
    return " ".join(words)


def next_session(calendar, time, filed):
    later = max(
        pd.Timestamp(time).tz_convert("America/New_York").strftime("%Y-%m-%d"), filed
    )
    i = calendar.searchsorted(later, side="right")
    return calendar[i] if i < len(calendar) else None


def get_sources(cfg):
    for file, digest in cfg["sec_hashes"].items():
        p = LOCAL / "raw" / file
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            resp = requests.get(cfg["sec_transport"] + file, timeout=120)
            resp.raise_for_status()
            tmp = p.with_suffix(".download")
            tmp.write_bytes(resp.content)
            checked(tmp, digest)
            tmp.replace(p)
        checked(p, digest)


def filings(db, cfg):
    get_sources(cfg)
    base = LOCAL / "raw"
    parent = pd.read_parquet(base / "filings.parquet")
    forms = parent[parent.form.isin(["10-K", "10-Q", "10-K/A", "10-Q/A"])].copy()
    forms = forms.dropna(
        subset=["accepted_utc", "filed_date", "company_name", "ticker"]
    )
    assert forms.adsh.is_unique
    # Verify the minute-resolution transport against filing headers for the manual audit.
    for accession, evidence in cfg["sec_control"].items():
        match = forms.adsh.eq(accession)
        assert match.sum() == 1
        actual = pd.Timestamp(evidence["accepted_et"])
        assert (
            abs((forms.loc[match, "accepted_utc"].iloc[0] - actual).total_seconds())
            < 60
        )
        forms.loc[match, "accepted_utc"] = actual.tz_convert("UTC")
        forms.loc[match, "accepted_et"] = actual.isoformat()
    sessions = pd.Index(
        sorted(pd.read_parquet(CAT / "prices.parquet", columns=["day"]).day.unique())
    )
    forms["available"] = [
        next_session(sessions, t, f)
        for t, f in zip(forms.accepted_utc, forms.filed_date)
    ]
    forms = forms[forms.available.le(cfg["decision"])].copy()

    def keys(frame):
        frame["issuer_key"] = frame.company_name.map(issuer)
        frame["symbol_key"] = frame.ticker.str.upper().str.replace(
            ".", "-", regex=False
        )
        return frame

    keys(forms)
    frozen = pd.read_parquet(CAT / "identifiers.parquet")
    hist = frozen.query(
        "country_flag=='Y' and security_type=='EQTY' and subtype=='COM' and share_type=='NS' and exchange in ['Q','A','N']"
    ).copy()
    hist = keys(hist.rename(columns={"issuer": "company_name"})).dropna(
        subset=["symbol_key"]
    )
    keep = ["issuer_key", "symbol_key", "permno", "id_from", "id_to"]
    links = forms.merge(hist[keep].drop_duplicates(), on=["issuer_key", "symbol_key"])
    obs = pd.to_datetime(links.filed_date).dt.date
    hist_ok = (obs >= links.id_from) & (obs <= links.id_to)
    # Validate date-specific 2026 price and volume on the last US session
    # on or before filing, plus the immutable year-end identity and matching public ticker.
    ext = pd.read_parquet(
        BR / "daily_extension.parquet",
        columns=["permno", "symbol", "day", "close", "volume"],
    )
    ext["day"] = pd.to_datetime(ext.day).dt.strftime("%Y-%m-%d")
    active = (
        ext[ext.close.gt(0) & ext.volume.gt(0)]
        .set_index(["permno", "day", "symbol"])
        .index
    )
    on_date = sessions[
        np.maximum(0, sessions.searchsorted(links.filed_date, side="right") - 1)
    ]
    continued = (
        (obs > date(2025, 12, 31))
        & (links.id_to == date(2025, 12, 31))
        & pd.MultiIndex.from_arrays([links.permno, on_date, links.symbol_key]).isin(
            active
        )
    )
    links = links[hist_ok | continued].drop_duplicates(["adsh", "permno"])
    links = links[links.groupby("adsh").permno.transform("size") == 1]
    links = links[links.groupby("permno").cik.transform("nunique") == 1].copy()
    links = links[
        [
            "adsh",
            "cik",
            "permno",
            "ticker",
            "form",
            "accepted_et",
            "accepted_utc",
            "filed_date",
            "available",
            "filing_url",
            "period_end",
        ]
    ].rename(columns={"period_end": "report_end"})
    # Multiple different values without a dimension ID are ambiguous.
    facts = pd.read_parquet(
        base / "facts.parquet",
        filters=[
            ("tag", "in", cfg["fundamental_tags"]),
            ("uom", "=", "USD"),
            ("taxonomy", "=", "us-gaap"),
            ("duration_quarters", "=", 0),
        ],
    )
    key = ["adsh", "cik", "tag", "period_end"]
    # Keep a filing's unique consolidated candidate only when the source agrees on value.
    unique = facts[key + ["value"]].dropna().drop_duplicates()
    unambiguous = unique[~unique.duplicated(key, keep=False)]
    versions = unambiguous.merge(links, on=["adsh", "cik"], validate="many_to_one")
    versions = versions[
        versions.period_end.le(versions.report_end)
        & versions.report_end.le(versions.filed_date)
    ]
    wide = (
        versions.pivot(
            index=[
                "permno",
                "ticker",
                "cik",
                "adsh",
                "period_end",
                "report_end",
                "filed_date",
                "available",
                "accepted_et",
                "filing_url",
                "form",
            ],
            columns="tag",
            values="value",
        )
        .dropna()
        .reset_index()
    )
    wide = wide[wide.Assets.gt(0) & wide.Liabilities.ge(0)].copy()
    wide["liabilities_to_assets"] = wide.Liabilities / wide.Assets
    wide = wide.sort_values(
        ["permno", "period_end", "available", "accepted_et", "adsh"]
    )
    keys2 = ["permno", "period_end"]
    prior = wide.groupby(keys2).shift()
    revised = wide[
        (wide.available > prior.available)
        & (abs(wide.Assets - prior.Assets) > 1)
        & (wide.period_end <= prior.report_end)
    ]
    wide["balance_sheet_class"] = np.where(
        wide.Assets >= wide.Liabilities,
        "Assets cover liabilities",
        "Liabilities exceed assets",
    )
    for accession, evidence in cfg["sec_control"].items():
        audited = wide[wide.adsh.eq(accession) & wide.period_end.eq("2025-09-30")]
        assert (
            len(audited) == 1
            and audited.Assets.iloc[0] == evidence["assets"]
            and audited.Liabilities.iloc[0] == evidence["liabilities"]
        )
    preferred = revised[revised.adsh.eq("0001628280-26-025211")]
    choices = preferred if not preferred.empty else revised
    later = choices.iloc[0]
    same = wide[(wide.permno == later.permno) & (wide.period_end == later.period_end)]
    original = same[same.available < later.available].iloc[-1]

    def asof(rows, day):
        return rows[rows.available <= day].iloc[-1]

    assert (
        asof(same, original.available).adsh
        == asof(same[same.available < later.available], original.available).adsh
    )
    assert asof(same, later.available).available == later.available
    assert (
        asof(same, original.available).balance_sheet_class
        == asof(
            same[same.available < later.available], original.available
        ).balance_sheet_class
    )
    view = (
        wide[wide.available.le(cfg["decision"])]
        .sort_values(["permno", "period_end", "available", "accepted_et", "adsh"])
        .drop_duplicates("permno", keep="last")
    )
    after = wide[wide.accepted_et.str[11:13].astype(int) >= 16]
    case = after[
        after.adsh.eq("0001615165-25-000027") & after.period_end.eq("2025-09-30")
    ].head(1)
    if case.empty:
        case = after.head(1)
    fields = [
        "ticker",
        "cik",
        "adsh",
        "period_end",
        "available",
        "form",
        "Assets",
        "Liabilities",
        "liabilities_to_assets",
        "accepted_et",
        "filing_url",
    ]
    return (
        {
            "forms_with_dates": len(forms),
            "matched_forms": len(links),
            "matched_securities": links.permno.nunique(),
            "usable_securities": len(view),
            "usable_versions": len(wide),
            "ambiguous_fact_keys": int(
                unique[unique.duplicated(key, keep=False)][key]
                .drop_duplicates()
                .shape[0]
            ),
            "source_quarters": sorted(parent.source_quarter.unique()),
            "changed_asset_pairs": len(revised),
            "original": records(original.to_frame().T[fields])[0],
            "later": records(later.to_frame().T[fields])[0],
            "after_close": records(case[fields])[0],
        },
        wide,
        view,
    )
