"""Retain source-labelled contract months and prices from a pinned research snapshot."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import gzip
import io
import json
import math
import re
from urllib.request import urlopen

from fetch_public_universe_data import ROOT, immutable_save

REVISION = "bbf5cf823e16be1cca27493a94099eb8cf33f6e7"
BASE = f"https://raw.githubusercontent.com/pst-group/pysystemtrade/{REVISION}"
FAMILIES = {
    "ES": "SP500",
    "NQ": "NASDAQ",
    "RTY": "RUSSELL_mini",
    "ZT": "US2",
    "ZF": "US5",
    "ZN": "US10",
    "ZB": "US20",
    "CL": "CRUDE_W",
    "GC": "GOLD",
    "6S": "CHF",
}


def acquire(item):
    root, name = item
    url = f"{BASE}/data/futures/multiple_prices_csv/{name}.csv"
    with urlopen(url, timeout=45) as response:
        raw = response.read(75_000_001)
    if len(raw) > 75_000_000:
        raise ValueError("Source exceeds size bound")
    days, contracts = set(), set()
    observations = 0
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        for role in ("PRICE", "FORWARD", "CARRY"):
            contract = row[role + "_CONTRACT"].split(".")[0]
            if not row[role] or not re.fullmatch(r"\d{4}(0[1-9]|1[012])\d{2}", contract):
                continue
            if math.isfinite(float(row[role])):
                days.add(datetime.fromisoformat(row["DATETIME"]).date().isoformat())
                contracts.add(contract[:6])
                observations += 1
    if not days:
        raise ValueError("No verified month-labelled prices")
    file = immutable_save(
        ROOT / "data/raw/research_futures" / REVISION, root, gzip.compress(raw, mtime=0), "csv.gz"
    )
    return dict(
        root=root,
        source=url,
        days=len(days),
        first=min(days),
        last=max(days),
        contract_months=len(contracts),
        role_observations=observations,
        file=file,
    )


def main():
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(acquire, FAMILIES.items()))
    result = dict(
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        revision=REVISION,
        rows=rows,
        limits="Research vendor prices and selected contract months. Historical exchange identity, settlement status and trading costs unverified.",
    )
    immutable_save(
        ROOT / "data/raw/research_futures" / REVISION,
        "receipt",
        json.dumps(result, indent=2).encode(),
        "json",
    )
    for row in rows:
        print(row["root"], row["first"], row["last"], row["contract_months"])


if __name__ == "__main__":
    main()
