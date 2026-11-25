"""Download complete US market sessions from a pinned public revision, without a ticker filter."""

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import zlib

from fetch_issuer_holdings import bil_rows
from fetch_public_market_bars import LAST, REVISION, query
from fetch_public_universe_data import ROOT, immutable_save

DEST = ROOT / "data/raw/public_sessions" / REVISION
FIELDS = ["act_symbol", "open", "high", "low", "close", "volume"]


def session(day):
    existing = list(DEST.glob(day + "-*.json.gz"))
    if len(existing) == 1:
        path = existing[0]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest[:16] != path.name[len(day) + 1 : len(day) + 17]:
            raise ValueError("Session fingerprint mismatch")
        count = len(json.loads(gzip.decompress(raw)))
        return dict(day=day, rows=count, file=dict(file=path.name, sha256=digest, size=len(raw)))
    sql = (
        "select left(act_symbol,1) as bucket,count(*) as n,"
        "to_base64(compress(json_arrayagg(json_array(act_symbol,open,high,low,close,volume)))) as bars "
        f"from ohlcv where date='{day}' group by left(act_symbol,1)"
    )
    buckets = query(sql)
    rows = []
    for bucket in buckets:
        payload = base64.b64decode(bucket["bars"])
        data = zlib.decompress(payload[4:])
        if len(data) != int.from_bytes(payload[:4], "little"):
            raise ValueError("Incomplete compressed bucket")
        batch = json.loads(data)
        if len(batch) != int(bucket["n"]) or any(
            len(r) != len(FIELDS) or not r[0].startswith(bucket["bucket"]) for r in batch
        ):
            raise ValueError("Incomplete symbol bucket")
        rows.extend(batch)
    if not rows or len({r[0] for r in rows}) != len(rows):
        raise ValueError("Missing session or duplicate symbol")
    raw = gzip.compress(json.dumps(sorted(rows), separators=(",", ":")).encode(), mtime=0)
    return dict(day=day, rows=len(rows), file=immutable_save(DEST, day, raw, "json.gz"))


def calendar():
    (sheet,) = (ROOT / "data/raw/issuer_nav").glob("SPY-*.xlsx")
    days = set()
    for row in bil_rows(sheet.read_bytes()):
        if not row:
            continue
        try:
            day = datetime.strptime(row[0], "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        if "2026-01-01" <= day <= LAST:
            days.add(day)
    return sorted(days)


def main():
    days = calendar()
    results = []
    errors = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {day: pool.submit(session, day) for day in reversed(days)}
        for day, job in tasks.items():
            try:
                results.append(job.result())
            except (ValueError, OSError, KeyError, zlib.error) as exc:
                errors[day] = str(exc)[:160]
    receipt = dict(
        revision=REVISION,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
        fields=FIELDS,
        calendar="Observed SPY issuer NAV dates",
        expected=days,
        sessions=results,
        errors=errors,
    )
    immutable_save(DEST, "receipt", json.dumps(receipt, indent=2).encode(), "json")
    print(len(results), len(errors), flush=True)


if __name__ == "__main__":
    main()
