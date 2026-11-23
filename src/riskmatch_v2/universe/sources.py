"""Additional exchange evidence for unresolved equities and newly priced IPOs."""

import gzip
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

import pandas as pd
from riskmatch_v2.archive_labels import read_snapshot

from ..equity_extension.fetch import atomic
from .data import BR
from .treasury import BASE

PUBLIC = BASE / "nasdaq"
API = "https://api.nasdaq.com/api/"


def get(path):
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (RiskMatch research)",
        "Accept": "application/json",
        "Referer": "https://www.nasdaq.com/",
    }
    for attempt in range(3):
        try:
            response = requests.get(API + path, headers=headers, timeout=18)
            if response.status_code == 429:
                time.sleep(int(response.headers.get("Retry-After") or 60))
            elif response.status_code in (400, 404):
                return json.dumps({"error": response.status_code}).encode()
            else:
                response.raise_for_status()
                response.json()
                return response.content
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
        time.sleep(2**attempt)
    raise ValueError("Source Nasdaq not available: " + path)


def load(name):
    return json.loads(gzip.decompress((PUBLIC / (name + ".json.gz")).read_bytes()))


def fetch_extra():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    inv = read_snapshot(BR / "inventory.parquet")
    symbols = sorted(
        set(
            s
            for v in inv.loc[inv.status.ne("complete"), "candidates"]
            for s in v.split(",")
            if re.fullmatch("[A-Z][A-Z0-9-]*", s)
        )
    )
    paths = {f"ipo-{i:02}": f"ipo/calendar?date=2026-{i:02}" for i in range(1, 11)}
    q = urlencode(
        dict(assetclass="stocks", fromdate="2025-11-01", todate="2026-10-30", limit=300)
    )
    paths.update({s: f"quote/{s}/historical?{q}" for s in symbols})

    def download(item):
        name, path = item
        out = PUBLIC / (name + ".json.gz")
        if not out.exists() or load(name).get("error") == 403:
            time.sleep(0.15)
            atomic(out, gzip.compress(get(path), mtime=0))

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(download, paths.items()))


def listing_log():
    rows = []
    for i in range(1, 11):
        doc = load(f"ipo-{i:02}")
        for r in (doc.get("data") or {}).get("priced", {}).get("rows") or []:
            rows.append(r)
    frame = pd.DataFrame(rows).drop_duplicates("dealID")
    frame["priced"] = pd.to_datetime(frame.pricedDate, format="mixed", errors="coerce")
    return frame[frame.priced.between("2026-01-01", "2026-10-30")]


def review():
    frame = read_snapshot(BR / "inventory.parquet")
    out = []
    for r in frame[frame.status.ne("complete")].itertuples():
        count = 0
        end_quote = None
        for name in r.candidates.split(","):
            if not (PUBLIC / (name + ".json.gz")).is_file():
                continue
            data = load(name).get("data") or {}
            quotes = (data.get("tradesTable") or {}).get("rows") or []
            end = next((q for q in quotes if q["date"] == "10/30/2026"), None)
            if end is not None and len(quotes) > count:
                count = len(quotes)
                end_quote = name
        out.append(
            dict(
                permno=r.permno,
                initial_status=r.status,
                rows_with_october=count,
                quote_symbol=end_quote,
            )
        )
    return pd.DataFrame(out)


if __name__ == "__main__":
    fetch_extra()


def additional_admissions(inventory, extension):
    """Review already identified series with the same CUSIP/price/return link as complete stocks."""
    audit = {}
    for pid, row in inventory[
        inventory.status.isin(["partial", "event to verify"])
    ].iterrows():
        symbol = row.symbol
        g = (
            extension.loc[extension.permno.eq(pid)]
            .sort_values("day")
            .tail(209)
            .set_index("day")
        )
        if (
            g.empty
            or not isinstance(symbol, str)
            or not (PUBLIC / (symbol + ".json.gz")).is_file()
        ):
            continue
        data = load(symbol).get("data") or {}
        rows = (data.get("tradesTable") or {}).get("rows") or []
        if not rows or data.get("symbol") != symbol:
            continue
        q = pd.DataFrame(rows)
        q.index = pd.to_datetime(q.date, format="%m/%d/%Y").dt.strftime("%Y-%m-%d")
        q = (
            q.close.str.replace(r"[^0-9.]", "", regex=True)
            .replace("", float("nan"))
            .astype(float)
            .sort_index()
        )
        if q.index.has_duplicates or "2026-10-30" not in q.index:
            continue
        last = g.tail(20)
        if not (
            g.index[-1] == "2026-10-30"
            and last.volume.iloc[-1] > 0
            and (last.volume > 0).sum() >= 18
            and last.close.iloc[-1] > 0
        ):
            continue
        if abs(q["2026-10-30"] / last.close.iloc[-1] - 1) > 0.005:
            continue
        ix = g.usd.gt(1) | g.usd.lt(-0.75)
        if ix.any():
            observed = q.reindex(g.index).pct_change(fill_method=None)[ix]
            error = (1 + observed) / (1 + g.usd[ix]) - 1
            if error.isna().any() or error.abs().max() > 0.02:
                continue
        if row.status == "event to verify" and (
            row.detail != "extreme daily variation" or not ix.any()
        ):
            continue
        typ = (
            "variation crossover on Nasdaq"
            if ix.any()
            else "partial series with recent liquidity and cross-cutting closing"
        )
        audit[int(pid)] = typ
    return audit
