"""Archive the US Treasury's FedInvest marks and reconstruct nominal coupon returns."""

import gzip
import json
import re
import threading
import time
import urllib.request as http
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import pandas as pd

from ..equity_extension.fetch import CAT, atomic

BASE = Path("data/local/univers")
RAW = BASE / "fedinvest"
URL = "https://www.treasurydirect.gov/GA-FI/FedInvest/"
API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
context = threading.local()


def session():
    if not hasattr(context, "client"):
        client = http.build_opener(http.HTTPCookieProcessor(CookieJar()))
        with client.open(URL + "selectSecurityPriceDate", timeout=30) as f:
            token = re.search(r'name="_csrf" value="([^"]+)', f.read().decode())[1]
        context.client, context.token = client, token
    return context.client, context.token


def download(day):
    path = RAW / (day + ".xml.gz")
    if path.exists():
        return
    d = pd.Timestamp(day)
    for attempt in range(4):
        try:
            client, token = session()
            payload = urlencode(
                dict(
                    priceDateDay=d.day,
                    priceDateMonth=d.month,
                    priceDateYear=d.year,
                    fileType="xml",
                    xml="XML FORMAT",
                    _csrf=token,
                )
            ).encode()
            with client.open(
                URL + "securityPriceDetail", data=payload, timeout=35
            ) as response:
                b = response.read()
            root = ET.fromstring(b)
            if not root.tag.endswith("FedInvestPriceData") or any(
                x.text != day for x in root.findall(".//PriceDate")
            ):
                raise ValueError("FedInvest returned data for a different date")
            atomic(path, gzip.compress(b, mtime=0))
            return
        except (OSError, ValueError, ET.ParseError):
            if hasattr(context, "client"):
                del context.client
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    holdings = pd.read_parquet(CAT / "holdings.parquet").dropna(subset=["coupon"])
    cusips = sorted(set(holdings.security))
    for ix in range(0, len(cusips), 20):
        filepath = RAW / f"auctions-{ix}.json"
        if not filepath.exists():
            params = urlencode(
                {
                    "filter": "cusip:in:(" + ",".join(cusips[ix : ix + 20]) + ")",
                    "page[size]": 1000,
                }
            )
            with http.urlopen(API + "?" + params, timeout=30) as f:
                blob = f.read()
            doc = json.loads(blob)
            if doc["links"]["next"]:
                raise ValueError("Incomplete auction history")
            atomic(filepath, blob)
    sessions = (
        pd.read_parquet(CAT / "prices.parquet", columns=["day"])
        .day.drop_duplicates()
        .sort_values()
    )
    for day in ("2008-09-12", "2008-11-20", "2026-11-20"):
        download(day)
    days = sessions[sessions.between("2014-10-01", "2026-10-30")].tolist()
    with ThreadPoolExecutor(5) as pool:
        for idx, _ in enumerate(pool.map(download, days[::-1]), 1):
            if idx % 300 == 0:
                print(idx, "/", len(days), flush=True)


if __name__ == "__main__":
    fetch()


def terms():
    tables = [
        pd.DataFrame(json.loads(p.read_bytes())["data"])
        for p in sorted(RAW.glob("auctions-*.json"))
    ]
    auctions = (
        pd.concat(tables)
        .sort_values("auction_date")
        .drop_duplicates("cusip")
        .set_index("cusip")
    )
    ids = (
        pd.read_parquet(CAT / "instruments.parquet")
        .query("asset_class=='obligation_directe'")
        .id.str[7:-1]
    )
    for cusip in set(ids) - set(auctions.index):
        path = RAW / f"security-{cusip}.json"
        if not path.exists():
            with http.urlopen(
                "https://www.treasurydirect.gov/TA_WS/securities/search?"
                + urlencode({"cusip": cusip, "format": "json"}),
                timeout=30,
            ) as f:
                atomic(path, f.read())
        entries = [r for r in json.loads(path.read_bytes()) if r.get("cusip") == cusip]
        if not entries:
            continue
        row = min(entries, key=lambda r: r["issueDate"])
        for col, key in [
            ("issue_date", "issueDate"),
            ("dated_date", "datedDate"),
            ("maturity_date", "maturityDate"),
            ("int_rate", "interestRate"),
            ("security_type", "securityType"),
        ]:
            auctions.loc[cusip, col] = str(row[key]).split("T00:")[0]
    return auctions.reindex(sorted(ids))


def accrual(dates, dated, maturity, rate):
    """Accrued interest and coupon entitlements per 100 par, on contractual dates."""
    end = pd.Timestamp(maturity)
    edges = [end]
    while edges[-1] > pd.Timestamp(dated):
        edges.append(edges[-1] - pd.DateOffset(months=6))
        if end.is_month_end:
            edges[-1] = edges[-1] + pd.offsets.MonthEnd(0)
    edges = pd.DatetimeIndex(edges[::-1])
    if edges[0] != pd.Timestamp(dated):
        raise ValueError("First irregular period to be documented")
    ds = pd.DatetimeIndex(dates)
    i = edges.searchsorted(ds, side="right") - 1
    ok = (i >= 0) & (i < len(edges) - 1)
    result = pd.Series(float("nan"), index=ds)
    j = i[ok]
    result.loc[ok] = (
        rate / 2 * (ds[ok] - edges[j]).days / (edges[j + 1] - edges[j]).days
    )
    coupon = pd.Series(i, index=ds).diff().clip(lower=0).fillna(0) * rate / 2
    coupon.loc[ds <= edges[0]] = 0.0
    return result, coupon


def history(days):
    import numpy as np

    cache = BASE / "bonds.parquet"
    import hashlib

    digest = hashlib.sha256(Path(__file__).read_bytes())
    for d in days:
        digest.update((RAW / (d + ".xml.gz")).read_bytes())
    for f in sorted(RAW.glob("*.json")):
        digest.update(f.read_bytes())
    signature = digest.hexdigest()
    meta = cache.with_suffix(".json")
    if cache.exists() and meta.exists():
        saved = json.loads(meta.read_bytes())
        if (
            saved["sources"] == signature
            and saved["file"] == hashlib.sha256(cache.read_bytes()).hexdigest()
        ):
            return pd.read_parquet(cache)
    securities = terms()
    marks = []
    for day in days:
        path = RAW / (day + ".xml.gz")
        if not path.is_file():
            raise FileNotFoundError(path)
        for sec in ET.fromstring(gzip.decompress(path.read_bytes())).iter("Security"):
            cusip = sec.findtext("Cusip")
            if cusip in securities.index:
                marks.append(
                    (
                        day,
                        cusip,
                        float(sec.findtext("EODPrice")),
                        float(sec.findtext("BuyPrice") or 0),
                        float(sec.findtext("SellPrice") or 0),
                    )
                )
    quotes = pd.DataFrame(marks, columns=["day", "cusip", "clean", "ask", "bid"])
    panels = []
    for cusip, row in securities.iterrows():
        if pd.isna(row.issue_date) or row.issue_date > days[-1]:
            continue
        dates = pd.DatetimeIndex(days)
        accrued, coupons = accrual(
            dates, row.dated_date, row.maturity_date, float(row.int_rate)
        )
        prices = quotes.loc[quotes.cusip.eq(cusip)].set_index("day").reindex(days)
        clean = prices.clean.where(prices.clean.gt(0)).to_numpy()
        dirty = pd.Series(clean, index=dates) + accrued
        dirty.loc[dates < pd.Timestamp(row.issue_date)] = np.nan
        # Entitlement moves to cash at next observed bond market price; ledger uses the same dates.
        observed = dirty.dropna()
        cumulative = coupons.cumsum().reindex(observed.index)
        earned = cumulative.diff().fillna(0.0)
        ret = (observed + earned) / observed.shift() - 1
        table = pd.DataFrame(
            dict(
                day=observed.index.strftime("%Y-%m-%d"),
                name="UST:" + cusip,
                close=observed.to_numpy(),
                clean=prices.reindex(
                    observed.index.strftime("%Y-%m-%d")
                ).clean.to_numpy(),
                income=earned.to_numpy(),
                usd=ret.to_numpy(),
                previous=observed.index.to_series()
                .shift()
                .dt.strftime("%Y-%m-%d")
                .to_numpy(),
            )
        )
        panels.append(table)
    all_rows = pd.concat(panels, ignore_index=True)
    tmp = cache.with_suffix(".tmp")
    all_rows.to_parquet(tmp, index=False)
    tmp.replace(cache)
    atomic(
        meta,
        json.dumps(
            dict(sources=signature, file=hashlib.sha256(cache.read_bytes()).hexdigest())
        ).encode(),
    )
    return all_rows


def bond_shock(terms_table, fx):
    # Only use endpoint marks when no intervening coupon needs a reinvestment mark.
    dates = ["2008-09-12", "2008-11-20"]
    marks = []
    for d in dates:
        download(d)
        root = ET.fromstring(gzip.decompress((RAW / (d + ".xml.gz")).read_bytes()))
        marks.append(
            {
                s.findtext("Cusip"): float(s.findtext("EODPrice"))
                for s in root.iter("Security")
            }
        )
    result = {}
    for k, r in terms_table.iterrows():
        if k not in marks[0] or k not in marks[1] or r.issue_date > dates[0]:
            continue
        accrued, coupon = accrual(
            dates, r.dated_date, r.maturity_date, float(r.int_rate)
        )
        if coupon.sum() == 0 and min(a[k] for a in marks) > 0:
            result["UST:" + k] = (marks[1][k] + accrued.iloc[1]) / (
                marks[0][k] + accrued.iloc[0]
            ) * fx[dates[1]] / fx[dates[0]] - 1
    return result


def latest_marks():
    day = "2026-11-20"
    root = ET.fromstring(gzip.decompress((RAW / (day + ".xml.gz")).read_bytes()))
    return {
        s.findtext("Cusip")
        for s in root.iter("Security")
        if float(s.findtext("EODPrice") or 0) > 0
    }
