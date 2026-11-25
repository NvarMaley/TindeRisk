"""Export a public-market date range from a local Dolt clone, then match private IDs offline."""

import argparse
import csv
from collections import Counter
import io
from datetime import datetime, timezone
from zipfile import ZipFile
import gzip
import json
from pathlib import Path
import re
import hashlib
import subprocess
import tempfile

import duckdb
from fetch_market_sessions import calendar
from fetch_public_market_bars import REVISION, LAST
from fetch_public_universe_data import ROOT, immutable_save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "clone",
        type=Path,
        nargs="?",
        help="If omitted, audit the downloaded whole-market session offline.",
    )
    parser.add_argument(
        "--zip", type=Path, help="ZIP from the public Dolt CSV endpoint at the configured revision."
    )
    parser.add_argument(
        "--sessions", action="store_true", help="Use complete locally downloaded market sessions."
    )
    parser.add_argument("--dolt", default="dolt")
    args = parser.parse_args()

    def sql(query):
        return [args.dolt, "sql", "-r", "csv", "-q", query]

    revision = REVISION
    if args.clone:
        revision = (
            subprocess.check_output(sql("select dolt_hashof('HEAD')"), cwd=args.clone, text=True)
            .splitlines()[-1]
            .strip()
        )
        if not re.fullmatch("[a-v0-9]{32}", revision):
            raise ValueError("Unknown Dolt revision")
    dest = ROOT / "data/raw/public_market_history" / revision
    dest.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect()
    report = json.loads((ROOT / "data/processed/universe/crsp_monthly_audit.json").read_text())
    cohort = set(report["selected_permnos"])
    (folder,) = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "new data")
    symbols = {}
    with (folder / "data_plus/raw/wrds/crsp_msf.csv").open() as stream:
        for r in csv.DictReader(stream):
            if r["PERMNO"] in cohort and r["MthCalDt"] == report["snapshot_date"]:
                symbols.setdefault(r["PERMNO"], set()).add(r["Ticker"])
    with tempfile.TemporaryDirectory(dir=dest) as temp:
        temp = Path(temp)
        csvfile = temp / "public.csv"
        if args.zip:
            with (
                ZipFile(args.zip) as archive,
                archive.open("ohlcv.csv") as stream,
                csvfile.open("wb") as out,
            ):
                if stream.readline().strip() != b"date,act_symbol,open,high,low,close,volume":
                    raise ValueError("Unexpected OHLCV schema")
                out.write(b"date,act_symbol,open,high,low,close,volume\n")
                for line in stream:
                    if b"2026-01-01" <= line[:10] <= LAST.encode():
                        out.write(line)
            db.execute("create table bars as select * from read_csv(?)", [str(csvfile)])
        elif args.sessions:
            folder = ROOT / "data/raw/public_sessions" / revision
            receipt = json.loads(
                max(folder.glob("receipt-*.json"), key=lambda p: p.stat().st_mtime_ns).read_text()
            )
            with csvfile.open("w") as stream:
                writer = csv.writer(stream)
                writer.writerow(["date", "act_symbol", "open", "high", "low", "close", "volume"])
                for part in receipt["sessions"]:
                    entry = part["file"]
                    raw = (folder / entry["file"]).read_bytes()
                    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                        raise ValueError("Corrupt market session")
                    writer.writerows(
                        [part["day"], *row] for row in json.loads(gzip.decompress(raw))
                    )
            db.execute("create table bars as select * from read_csv(?)", [str(csvfile)])
        elif args.clone:
            with csvfile.open("wb") as stream:
                subprocess.run(
                    sql(f"select * from ohlcv where date >= '2026-01-01' and date <= '{LAST}'"),
                    cwd=args.clone,
                    stdout=stream,
                    check=True,
                )
            db.execute("create table bars as select * from read_csv(?)", [str(csvfile)])
        else:
            folder = ROOT / "data/raw/public_market_bars" / revision
            (path,) = folder.glob(f"market-{LAST}-*.json.gz")
            if (
                hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                != path.name.split("-")[-1].split(".")[0]
            ):
                raise ValueError("Market snapshot fingerprint mismatch")
            db.execute(
                "create table bars as select act_symbol,cast(date as date) as date, cast(open as double) as open, cast(high as double) as high, cast(low as double) as low, cast(close as double) as close, cast(volume as bigint) as volume from read_json_auto(?)",
                [str(path)],
            )
        total, unique = db.execute(
            "select count(*),count(distinct (act_symbol,date)) from bars"
        ).fetchone()
        if not total or total != unique:
            raise ValueError("Empty or duplicate symbol/day pairs")
        data = temp / "bars.parquet"
        db.execute("copy bars to '" + str(data) + "' (format parquet)")
        entry = immutable_save(dest, "market-bars", data.read_bytes(), "parquet")
    db.execute("""create view valid as select * from bars where close>0 and least(open,close)>=low
               and greatest(open,close)<=high and low>0 and volume>=0
               and isfinite(open) and isfinite(close) and isfinite(low) and isfinite(high)""")
    days = int(db.execute("select count(distinct date) from valid").fetchone()[0])
    coverage = {
        s: n
        for s, n in db.execute(
            "select act_symbol,count(*) from valid group by act_symbol"
        ).fetchall()
    }
    expected = set(calendar())
    observed = {str(day) for (day,) in db.execute("select distinct date from valid").fetchall()}
    aliases = {permno: next(iter(values)) for permno, values in symbols.items() if len(values) == 1}
    frequencies = Counter(aliases.values())
    current_day = dict(
        db.execute(
            "select act_symbol, count(*) from valid where date=? group by act_symbol", [LAST]
        ).fetchall()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["local_permno", "snapshot_ticker", "sessions", "observed_on_last_date", "match_status"]
    )
    matched = []
    last_count = 0
    for permno in sorted(cohort):
        symbol = aliases.get(permno, "")
        unique_alias = bool(symbol) and frequencies[symbol] == 1
        sessions = coverage.get(symbol, 0) if unique_alias else 0
        last_count += bool(current_day.get(symbol)) and unique_alias
        matched.append(sessions)
        status = (
            "unambiguous_snapshot_ticker" if unique_alias and sessions else "unmatched_or_ambiguous"
        )
        writer.writerow(
            [permno, symbol, sessions, int(unique_alias and bool(current_day.get(symbol))), status]
        )
    match_file = immutable_save(
        ROOT / "data/processed/universe/market_matches",
        "coverage",
        gzip.compress(buffer.getvalue().encode(), mtime=0),
        "csv.gz",
    )
    details = dict(
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        revision=revision,
        source="https://www.dolthub.com/repositories/post-no-preference/stocks",
        file=entry,
        rows=total,
        invalid=total - sum(coverage.values()),
        days=days,
        first=str(db.execute("select min(date) from valid").fetchone()[0]),
        last=str(db.execute("select max(date) from valid").fetchone()[0]),
        tickers=len(coverage),
        expected_days=len(expected),
        missing_days=sorted(expected - observed),
        unexpected_days=sorted(observed - expected),
        cohort_size=len(cohort),
        cohort_last=last_count,
        local_match_file=match_file,
        cohort_any=sum(n > 0 for n in matched),
        cohort_all_sessions=matched.count(len(expected)) if expected == observed else 0,
        etf_days={t: coverage.get(t, 0) for t in report["etf"]},
        limits="Dated ticker matches only. Verify identifier continuity, adjustment convention and delistings before use.",
    )
    immutable_save(dest, "receipt", json.dumps(details, indent=2).encode(), "json")
    print({k: v for k, v in details.items() if k != "file"}, flush=True)


if __name__ == "__main__":
    main()
