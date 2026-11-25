"""Acquire spot crypto observations and issue-specific Treasury inflation ratios."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timezone
import gzip
import io
import json
import math
import re
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, FRED_CSV, immutable_save, request


def spot(series, cutoff, dest):
    url = FRED_CSV + "?" + urlencode({"id": series, "coed": cutoff})
    raw = request(url)
    observed = {}
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        day = date.fromisoformat(row["observation_date"]).isoformat()
        price = row[series]
        if day > cutoff or day in observed:
            raise ValueError("Invalid date or duplicate")
        if price not in ("", "."):
            if not math.isfinite(float(price)) or float(price) <= 0:
                raise ValueError("Invalid spot price")
            observed[day] = float(price)
    return dict(dataset=series, rows=len(observed), first_record=min(observed), last_record=max(observed),
                kind="Coinbase USD spot observation via FRED", source=url,
                files=[immutable_save(dest, series, raw, "csv")], status="downloaded_schema_checked_not_normalized")


def tips(cusip, cutoff, dest):
    if not re.fullmatch("[0-9A-Z]{9}", cusip):
        raise ValueError("Invalid CUSIP")
    url = "https://www.treasurydirect.gov/TA_WS/secindex/search?" + urlencode({"cusip": cusip, "format": "json"})
    raw = request(url)
    days = set()
    for row in json.loads(raw):
        day = date.fromisoformat(row["indexDate"][:10]).isoformat()
        if row["cusip"] != cusip or row["indexType"] != "CPI":
            raise ValueError("Unexpected identity")
        if day > cutoff:
            continue
        ratio = float(row["indexRatio"])
        if day in days or not math.isfinite(ratio) or ratio <= 0:
            raise ValueError("Invalid daily ratio")
        days.add(day)
    if not days:
        raise ValueError("No historical ratios returned")
    return dict(cusip=cusip, source=url, rows=len(days), first=min(days), last=max(days),
                file=immutable_save(dest, cusip, gzip.compress(raw, mtime=0), "json.gz"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=["tips", "crypto"])
    mode = parser.parse_args().dataset
    cutoff = date.today().isoformat()
    if mode == "crypto":
        dest = ROOT / "data/raw/public_universe" / cutoff
        rows = [spot(s, cutoff, dest) for s in ("CBBTCUSD", "CBETHUSD")]
        receipt = dict(schema="public-source-receipt-v1", acquired_at_utc=datetime.now(timezone.utc).isoformat(), datasets=rows)
    else:
        dest = ROOT / "data/raw/tips_ratios" / cutoff
        master = json.loads((ROOT / "data/processed/universe/treasury_identity.json").read_text())
        ids = sorted({row["cusip"] for row in master["rows"] if row["instrument_type"] == "tips"})
        def acquire(cusip):
            try:
                return tips(cusip, cutoff, dest)
            except (OSError, ValueError, KeyError) as exc:
                return {"cusip": cusip, "error": str(exc)}
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(acquire, ids))
        receipt = dict(cutoff=cutoff, acquired_at_utc=datetime.now(timezone.utc).isoformat(), issues=rows)
    immutable_save(dest, "receipt", json.dumps(receipt, indent=2).encode(), "json")
    print(mode, len(rows), sum(r.get("rows", 0) for r in rows), [r for r in rows if "error" in r])


if __name__ == "__main__":
    main()
