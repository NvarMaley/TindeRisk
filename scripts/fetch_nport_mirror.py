"""Retrieve only the configured SEC series from the public N-PORT research mirror."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request

DATASET = "ZipLime/fund-holdings-nport"
ENDPOINT = "https://datasets-server.huggingface.co/filter?"
DEST = ROOT / "data/raw/nport_research_mirror"


def fetch(target):
    series = target["series_id"]
    summary = {"ticker": target["ticker"], "series": series}
    for config in ("filings", "holdings"):
        rows = []
        partial = False
        while True:
            args = dict(
                dataset=DATASET,
                config=config,
                split="train",
                where='"series_id" = \'' + series + "'",
                offset=len(rows),
                length=100,
            )
            page = json.loads(request(ENDPOINT + urlencode(args)))
            batch = [v["row"] for v in page["rows"]]
            total = page["num_rows_total"]
            if any(r["series_id"] != series for r in batch) or (not batch and len(rows) < total):
                raise ValueError("Invalid filtered page")
            partial |= bool(page.get("partial"))
            rows.extend(batch)
            if len(rows) >= total:
                break
        if not rows:
            summary[config] = dict(rows=0, partial=partial)
            continue
        keys = {(r["accession_number"], r.get("holding_id")) for r in rows}
        if len(keys) != len(rows):
            raise ValueError("Duplicate filing or holding encountered")
        dates = sorted({r["report_date"] for r in rows})
        raw = gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0)
        file = immutable_save(DEST, target["ticker"] + "-" + config, raw, "json.gz")
        summary[config] = dict(
            rows=len(rows),
            reports=len(dates),
            first=dates[0],
            last=dates[-1],
            partial=partial,
            file=file,
        )
    print(target["ticker"], summary, flush=True)
    return summary


def main():
    targets = json.loads((ROOT / "configs/sec_nport_targets.json").read_text())["targets"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, targets))
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(
                dataset=DATASET, acquired_at_utc=datetime.now(timezone.utc).isoformat(), funds=rows
            ),
            indent=2,
        ).encode(),
        "json",
    )


if __name__ == "__main__":
    main()
