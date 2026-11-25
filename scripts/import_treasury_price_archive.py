"""Read dated JSON members of the pinned CUSIP-Set archive; never execute archive contents."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import zipfile

from fetch_public_universe_data import ROOT, immutable_save

REVISION = "6de1472c7feb048d8bcfcc261d9a6a1dcac71eed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    base = ROOT / "data/raw/treasury_archive"
    base.mkdir(parents=True, exist_ok=True)
    ids = {r["cusip"]:r for r in json.loads((ROOT / "data/processed/universe/treasury_identity.json").read_text())["rows"]}
    counts = Counter()
    dates = set()
    duplicates = conflicts = 0
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        output = Path(tmp) / "observations.csv.gz"
        with zipfile.ZipFile(args.archive) as archive, gzip.open(output, "wt", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["date", "cusip", "instrument_type", "bid_price", "offer_price", "mid_price", "eod_price"])
            for member in sorted(archive.namelist()):
                match = re.fullmatch(r"CUSIP-Set-" + REVISION + r"/(\d{4}-\d\d-\d\d)\.json", member)
                if not match:
                    continue
                day = match[1]
                by_id = {}
                for row in json.loads(archive.read(member))["data"]:
                    cusip = row["cusip"]
                    identity = ids.get(cusip)
                    if not identity or not identity["first_observed_issue_date"] <= day <= identity["maturity"]:
                        continue
                    values = tuple(row.get(field) for field in ("bid_price","offer_price","mid_price","eod_price"))
                    if not any(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in values):
                        continue
                    if cusip in by_id:
                        duplicates += 1
                        if by_id[cusip] != values:
                            by_id[cusip] = None
                            conflicts += 1
                    else:
                        by_id[cusip] = values
                for cusip, values in by_id.items():
                    if values is None:
                        continue
                    kind = ids[cusip]["instrument_type"]
                    writer.writerow([day, cusip, kind, *values])
                    counts[kind] += 1
                    dates.add(day)
        with args.archive.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        record = dict(source=f"https://github.com/yieldcurvemonkey/CUSIP-Set/tree/{REVISION}", archive_sha256=digest,
                      acquired_at_utc=datetime.now(timezone.utc).isoformat(), days=len(dates), first=min(dates),
                      last=max(dates), rows_by_family=counts, duplicate_rows=duplicates, conflict_events=conflicts,
                      file=immutable_save(base,"cusip-set",output.read_bytes(),"csv.gz"))
    immutable_save(base,"receipt",json.dumps(record,indent=2).encode(),"json")
    print(record)


if __name__ == "__main__":
    main()
