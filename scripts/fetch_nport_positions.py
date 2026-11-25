"""Read public filing positions for identified accessions from pinned quarterly Parquet files."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
import os
import re

import duckdb
from fetch_public_universe_data import ROOT, immutable_save

REV = "a9ace4083d364415e6e558c3514d9e6aa3519519"
SRC = ROOT / "data/raw/nport_research_mirror"
DEST = ROOT / "data/raw/nport_accession_positions" / REV


def fetch(item):
    quarter, filings = item
    year, number = quarter.split("q")
    url = f"https://huggingface.co/datasets/trader298/sec-nport/resolve/{REV}/FUND_REPORTED_HOLDING/year={year}/quarter={number}/data.parquet"
    settings = {"threads": "2"}
    if os.environ.get("DUCKDB_EXTENSION_DIRECTORY"):
        settings["extension_directory"] = os.environ["DUCKDB_EXTENSION_DIRECTORY"]
    db = duckdb.connect(config=settings)
    try:
        fields = "ACCESSION_NUMBER,HOLDING_ID,ISSUER_NAME,ISSUER_CUSIP,CURRENCY_CODE,CURRENCY_VALUE,PERCENTAGE,ASSET_CAT,ISSUER_TYPE"
        ids = sorted(filings)
        params = ",".join("?" for _ in ids)
        result = db.execute(
            f"SELECT {fields} FROM read_parquet(?) WHERE ACCESSION_NUMBER IN ({params}) ORDER BY ACCESSION_NUMBER,HOLDING_ID",
            [url, *ids],
        )
        rows = [dict(zip(fields.lower().split(","), r)) for r in result.fetchall()]
    finally:
        db.close()
    if len({(r["accession_number"], r["holding_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate holdings")
    counts = defaultdict(int)
    for row in rows:
        counts[row["accession_number"]] += 1
    file = immutable_save(
        DEST, quarter, gzip.compress(json.dumps(rows, default=str).encode(), mtime=0), "json.gz"
    )
    item = dict(
        quarter=quarter,
        source=url,
        file=file,
        expected=len(filings),
        found=len(counts),
        rows=len(rows),
    )
    print(quarter, len(counts), len(filings), len(rows), flush=True)
    return item


def main():
    quarters = defaultdict(dict)
    receipt = json.loads(
        max(SRC.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime).read_text()
    )
    for fund in receipt["funds"]:
        with gzip.open(SRC / fund["filings"]["file"]["file"]) as f:
            for row in json.load(f):
                q = row["source_quarter"]
                if not re.fullmatch(r"20\d\dq[1-4]", q):
                    raise ValueError("Invalid filing quarter")
                quarters[q][row["accession_number"]] = fund["ticker"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {q: pool.submit(fetch, (q, filings)) for q, filings in sorted(quarters.items())}
        results = []
        for q, job in jobs.items():
            try:
                results.append(job.result())
            except (OSError, ValueError, duckdb.Error) as exc:
                results.append(dict(quarter=q, error=type(exc).__name__))
                print(q, str(exc)[:180], flush=True)
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), quarters=results), indent=2
        ).encode(),
        "json",
    )


if __name__ == "__main__":
    main()
