"""Collect official valuation marks on the last observed nominal-curve day of each month."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timezone
import io
import json

from fetch_public_universe_data import ROOT, immutable_save
from fetch_fedinvest_prices import fetch, parse, HEADER, URL


def collect(day):
    dest = ROOT / "data/raw/fedinvest" / day.isoformat()
    if list(dest.glob("receipt-*.json")):
        return
    rows = parse(fetch(day), day)
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(["date", *HEADER])
    w.writerows([[day.isoformat(), *r] for r in rows])
    file = immutable_save(dest, "prices", s.getvalue().encode(), "csv")
    receipt = dict(
        date=day.isoformat(),
        source=URL,
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        rows=len(rows),
        types=dict(Counter(r[1] for r in rows)),
        file=file,
        kind="government valuation marks",
    )
    immutable_save(dest, "receipt", json.dumps(receipt, indent=2).encode(), "json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--daily-since",
        type=date.fromisoformat,
        help="Collect every observed curve session from this date.",
    )
    parser.add_argument(
        "--daily-through",
        type=date.fromisoformat,
        default=date.today(),
        help="Last requested curve date.",
    )
    parser.add_argument("--oldest-first", action="store_true")
    args = parser.parse_args()
    files = sorted((ROOT / "data/raw/public_universe").glob("*/fred-DGS10-*.csv"))
    if not files:
        raise ValueError("A local DGS10 file is required")
    month_ends = {}
    daily = set()
    with files[-1].open() as stream:
        for r in csv.DictReader(stream):
            day = r["observation_date"]
            if (
                args.daily_since
                and args.daily_since.isoformat() <= day < date.today().isoformat()
                and day <= args.daily_through.isoformat()
                and r["DGS10"] not in ("", ".")
            ):
                daily.add(date.fromisoformat(day))
            if (
                day >= "2008-09-02"
                and day[:7] < date.today().isoformat()[:7]
                and r["DGS10"] not in ("", ".")
            ):
                month_ends[day[:7]] = date.fromisoformat(day)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {
            day: pool.submit(collect, day)
            for day in sorted(
                daily if args.daily_since else month_ends.values(), reverse=not args.oldest_first
            )
        }
        for day, job in jobs.items():
            try:
                job.result()
            except (ValueError, OSError) as exc:
                print(day, str(exc)[:110], flush=True)


if __name__ == "__main__":
    main()
