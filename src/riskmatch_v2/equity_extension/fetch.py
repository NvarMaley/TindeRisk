"""Cache public evidence for each candidate symbol of the December 2025 cohort."""

import gzip
import io
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

CAT = Path("data/local/4/4.0-2026-11-23")
BASE = Path("data/local/actions-2026/2026-10-30")
RAW = BASE / "raw"
DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
END = "2026-10-30"
ANCHOR = "2025-12-31"


def atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def get(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (RiskMatch research)",
            "Accept-Encoding": "gzip",
        },
    )
    with urlopen(req, timeout=25) as response:
        body = response.read()
        return (
            gzip.decompress(body)
            if response.getheader("Content-Encoding") == "gzip"
            else body
        )


def cohort():
    active = pd.read_parquet(CAT / "replay_2025.parquet").query("trading == 'A'")
    names = pd.read_parquet(
        CAT / "stock_months.parquet",
        filters=[("day", "=", date.fromisoformat(ANCHOR))],
        columns=["permno", "issuer", "cusip", "exchange"],
    )
    return active.merge(names, on="permno", validate="one_to_one").sort_values("permno")


def candidate_symbols(cohort, symbols):
    # CRSP can use one root for multiple share classes. Price overlap decides the class.
    aliases = {}
    for symbol in symbols:
        match = re.fullmatch(r"([A-Z]+)[.-]([A-D])", str(symbol))
        if match:
            aliases.setdefault(match[1], set()).add("-".join(match.groups()))
    return {
        root: sorted({root, *aliases.get(root, ())})
        for root in set(cohort.ticker.dropna())
    }


def chart_url(symbol):
    def stamp(day):
        return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())

    query = urlencode(
        dict(
            period1=stamp("2025-11-01"),
            period2=stamp("2026-10-31"),
            interval="1d",
            events="div,splits",
            includeAdjustedClose="true",
        )
    )
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    directory = RAW / "nasdaqtraded.txt"
    if not directory.exists():
        atomic(directory, get(DIRECTORY))
    df = pd.read_csv(io.BytesIO(directory.read_bytes()), sep="|")
    directory_symbols = df.loc[(df["Test Issue"] == "N") & (df["ETF"] == "N"), "Symbol"]
    from .identity import references

    rows = cohort()
    candidates = candidate_symbols(rows, directory_symbols)
    aliases, _, _ = references(rows, download=True)
    candidates.update({f"id:{k}": v for k, v in aliases.items()})
    symbols = sorted(
        {s for candidates_for_root in candidates.values() for s in candidates_for_root}
    )
    meta_path = RAW / "receipts.json"
    records = json.loads(meta_path.read_bytes()) if meta_path.exists() else {}
    gate = Lock()
    next_request = [0.0]

    def download(symbol):
        path = RAW / (symbol + ".json.gz")
        old = records.get(symbol, {})
        if (old.get("status") == "ok" and path.exists()) or old.get("status") in (
            "HTTP 404",
            "HTTP 400",
        ):
            return symbol, old
        url = chart_url(symbol)
        record = dict(url=url, retrieved=datetime.now(timezone.utc).isoformat())
        for attempt in range(3):
            with gate:
                time.sleep(max(0, next_request[0] - time.monotonic()))
                next_request[0] = time.monotonic() + 0.11
            try:
                body = get(url)
                doc = json.loads(body)
                if not doc["chart"].get("result"):
                    raise ValueError(str(doc["chart"].get("error")))
                atomic(path, gzip.compress(body, mtime=0))
                return symbol, record | dict(status="ok")
            except HTTPError as exc:
                if exc.code == 429:
                    delay = exc.headers.get("Retry-After", "")
                    with gate:
                        next_request[0] = max(
                            next_request[0],
                            time.monotonic() + (int(delay) if delay.isdigit() else 60),
                        )
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    return symbol, record | dict(status=f"HTTP {exc.code}")
            except (ValueError, TimeoutError, URLError, OSError) as exc:
                if attempt == 2:
                    return symbol, record | dict(status=type(exc).__name__)
            time.sleep(2**attempt)

    with ThreadPoolExecutor(max_workers=5) as pool:
        for i, (symbol, record) in enumerate(pool.map(download, symbols), 1):
            records[symbol] = record
            if i % 100 == 0:
                atomic(meta_path, json.dumps(records, sort_keys=True).encode())
                print(i, "/", len(symbols), flush=True)
    atomic(meta_path, json.dumps(records, sort_keys=True).encode())


if __name__ == "__main__":
    main()
