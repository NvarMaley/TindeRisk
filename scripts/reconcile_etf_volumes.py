"""Join the two daily WRDS deliveries for candidate ETFs, excluding conflicting keys."""
from collections import Counter
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def insert_unique(store, key, value):
    if key not in store:
        store[key] = value
    elif store[key] != value:
        store[key] = None


def main():
    dest = ROOT / "data/processed/universe"
    base = {}
    with (dest / "crsp_etf_daily_extract.csv").open(newline="") as s:
        for r in csv.DictReader(s):
            insert_unique(base, (r["PERMNO"], r["DlyCalDt"]), (r["catalog_ticker"], r["DlyPrc"], r["DlyRet"], r["DlyBid"], r["DlyAsk"]))
    ids = {key[0] for key in base}
    audit = json.loads((dest / "wrds_delivery.json").read_text())["tables"]["daily_supplement"]
    folder, = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "telecharger")
    source = folder / audit["file"]
    if source.stat().st_mtime_ns != audit["mtime_ns"]:
        raise ValueError("Audit expired")
    volume = {}
    with source.open(newline="") as s:
        reader = csv.reader(s)
        header = next(reader)
        pi, di, vi, ri = map(header.index, ("PERMNO", "DlyCalDt", "DlyVol", "DlyRet"))
        for r in reader:
            if r[pi] in ids and (r[pi], r[di]) in base:
                insert_unique(volume, (r[pi], r[di]), (r[vi], r[ri]))
    if source.stat().st_mtime_ns != audit["mtime_ns"]:
        raise ValueError("Source changed")
    coverage = Counter()
    excluded = Counter()
    with TemporaryDirectory(dir=dest) as tmp:
        output = Path(tmp) / "etf_daily_volume.csv.gz"
        with gzip.open(output, "wt", newline="") as s:
            writer = csv.writer(s)
            writer.writerow(["ticker","permno","date","price","total_return","bid","ask","volume"])
            for key, price in sorted(base.items()):
                if not price or not volume.get(key):
                    excluded["missing_or_conflicting_key"] += 1
                    continue
                vol, ret = volume[key]
                try:
                    if Decimal(ret) != Decimal(price[2]):
                        excluded["inconsistent_return"] += 1
                        continue
                    if not Decimal(vol).is_finite() or Decimal(vol) < 0:
                        raise InvalidOperation
                except InvalidOperation:
                    excluded["missing_or_invalid_fields"] += 1
                    continue
                writer.writerow([price[0],*key,*price[1:],vol])
                coverage[price[0]] += 1
        if not coverage:
            raise ValueError("Empty join")
        report = dict(audited_on=date.today().isoformat(),source_keys=len(base),matched=sum(coverage.values()),
                      by_ticker=coverage,excluded=excluded)
        manifest = Path(tmp) / "etf_daily_volume.json"
        manifest.write_text(json.dumps(report,indent=2))
        output.replace(dest / output.name)
        manifest.replace(dest / manifest.name)
        print(report)


if __name__ == "__main__":
    main()
