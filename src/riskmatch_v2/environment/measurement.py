"""Ownership-weighted US point-source emissions and comparable calendar-year sales."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

from ..library.sources import checked, issuer_code
from ..stocks.filings import issuer
from ..universe.data import BR

LOCAL = Path("data/local/11")
REPORT = Path("reports/11-environment")
EPA = "https://www.epa.gov/system/files/other-files/2024-10/"
SOURCES = {
    "2023_data_summary_spreadsheets.zip": "895349c8008b7962dba68659c8187cec6b340d68be84ccb3f0e7fb6037bf8345",
    "ghgp_data_parent_company.xlsb": "5613dd8454b08deb160e3f1dec18c1a9b45464bc0ef8453c97989ea0d4fdbce2",
}
CUTOFF = "2026-10-30T23:59:59Z"
REVIEW = "2026-11-23T14:00:00Z"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def fetch():
    raw = LOCAL / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name, checksum in SOURCES.items():
        dest = raw / name
        if not dest.exists():
            response = requests.get(EPA + name, timeout=120)
            response.raise_for_status()
            temp = dest.with_suffix(".download")
            temp.write_bytes(response.content)
            checked(temp, checksum)
            temp.replace(dest)
        checked(dest, checksum)
    return raw


def allocate(facilities, owners):
    """Reject the entire facility if its ownership schedule fails reconciliation."""
    if (
        not facilities.id.is_unique
        or not np.isfinite(facilities.tonnes).all()
        or (facilities.tonnes < 0).any()
    ):
        raise ValueError("Invalid direct point emitter totals")
    rows = owners.merge(facilities, on="id", validate="many_to_one")
    valid = (
        rows.parent.notna()
        & rows.share.between(0, 100)
        & ~rows.duplicated(["id", "parent"], keep=False)
    )
    eligible = valid.groupby(rows.id).transform("all") & rows.groupby(
        "id"
    ).share.transform("sum").sub(100).abs().le(0.01)
    good = rows.loc[eligible & rows.share.gt(0)].copy()
    good["attributed"] = good.tonnes * good.share / 100
    return good


def sources():
    raw = fetch()
    with zipfile.ZipFile(raw / next(iter(SOURCES))) as archive:
        frame = pd.read_excel(
            io.BytesIO(archive.read("ghgp_data_2023.xlsx")),
            engine="calamine",
            sheet_name="Direct Point Emitters",
            header=3,
            usecols=["Facility Id", "Total reported direct emissions"],
        )
    frame.columns = ["id", "tonnes"]
    owners = pd.read_excel(
        raw / "ghgp_data_parent_company.xlsb",
        engine="calamine",
        sheet_name="2023",
        usecols=[
            "GHGRP FACILITY ID",
            "PARENT COMPANY NAME",
            "PARENT CO. PERCENT OWNERSHIP",
        ],
    )
    owners.columns = ["id", "parent", "share"]
    good = allocate(frame, owners)
    parents = (
        good.groupby("parent")
        .agg(tonnes=("attributed", "sum"), facilities=("id", "nunique"))
        .reset_index()
    )
    parents["key"] = parents.parent.map(issuer)
    parents = parents[~parents.key.duplicated(keep=False) & parents.key.ne("")]
    inv_path = BR / "inventory.parquet"
    inventory = pd.read_parquet(inv_path)
    inventory["code"] = inventory.cusip_2025.map(issuer_code).where(
        inventory.cusip_confirmed.eq(True)
    )
    archive = json.loads(Path("reports/09-stocks/results.json").read_text())["archive"]
    link_path = Path("data/local/9") / archive / "current_fundamentals.parquet"
    linked = pd.read_parquet(link_path).dropna(subset=["cik"])
    facts = Path("data/local/9/raw/facts.parquet")
    # Use the most recent eligible annual filing with a comparable revenue tag.
    cfg = json.loads(Path("config/stocks-9.json").read_text())
    checked(facts, cfg["sec_hashes"]["facts.parquet"])
    sales = duckdb.sql(
        """
        with versions as (
          select cik, adsh, accepted_utc, company_name, tag, min(value) as revenue, count(distinct value) as n
          from read_parquet(?) where taxonomy='us-gaap' and uom='USD' and form in ('10-K','10-K/A')
          and period_end='2023-12-31' and duration_quarters=4 and accepted_utc <= cast(? as timestamptz)
          and tag in ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet')
          group by all
        )
        select * from versions qualify row_number() over(partition by cik order by accepted_utc desc, adsh desc,
        case tag when 'RevenueFromContractWithCustomerExcludingAssessedTax' then 0 when 'Revenues' then 1 else 2 end)=1
        order by cik
    """,
        params=[str(facts), CUTOFF],
    ).df()
    sales["cik"] = sales.cik.astype(int)
    sales["key"] = sales.company_name.map(issuer)
    linked["cik"] = linked.cik.astype(int)
    rows = (
        inventory.dropna(subset=["code"])
        .merge(linked[["permno", "cik"]], on="permno", validate="one_to_one")
        .merge(sales, on="cik", validate="many_to_one")
    )
    rows = rows[
        (rows.n == 1)
        & rows.revenue.gt(0)
        & (
            rows.key.eq(rows.issuer.map(issuer))
            | rows.key.eq(rows.public_name.map(issuer))
        )
    ].copy()
    rows = rows[
        rows.groupby("code").cik.transform("nunique").eq(1)
        & rows.groupby("key").cik.transform("nunique").eq(1)
    ]
    measured = rows.merge(parents, on="key", validate="many_to_one").sort_values(
        "permno"
    )
    measured["intensity"] = measured.tonnes * 1e6 / measured.revenue
    measured.to_parquet(LOCAL / "issuer_measurements.parquet", index=False)
    return (
        inventory,
        measured,
        {
            "point_facilities": len(frame),
            "ownership_reconciled": int(good.id.nunique()),
            "excluded_facilities": int(len(frame) - good.id.nunique()),
            "measured_issuers": int(measured.cik.nunique()),
            "hashes": {p.name: digest(p) for p in [inv_path, link_path, facts]},
            "epa_hashes": SOURCES,
        },
    )
