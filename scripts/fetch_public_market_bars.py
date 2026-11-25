"""Read one complete public market session from a pinned public database."""

from datetime import datetime, timezone
import gzip
import json
import hashlib
import math
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request

REVISION = "njs8j85h7atjqje4ldfu4c4lillpka3t"
BASE = "https://www.dolthub.com/api/v1alpha1/post-no-preference/stocks/master"
DEST = ROOT / "data/raw/public_market_bars" / REVISION
LAST = "2026-11-23"


def query(sql):
    sql = sql.replace("from ohlcv where", f"from ohlcv as of '{REVISION}' where")
    response = json.loads(request(BASE + "?" + urlencode({"q": sql})))
    if response["query_execution_status"] != "Success":
        raise ValueError(response["query_execution_message"])
    return response["rows"]


def fetch(label, condition):
    paths = list(DEST.glob(label + "-*.json.gz"))
    if len(paths) == 1:
        path = paths[0]
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest()[:16] != path.name.split("-")[-1].split(".")[0]:
            raise ValueError("Stored session fingerprint mismatch")
        rows = json.loads(gzip.decompress(content))
    else:
        count = int(query("select count(*) as n from ohlcv where " + condition)[0]["n"])
        rows = []
        for offset in range(0, count, 1000):
            rows.extend(
                query(
                    f"select * from ohlcv where {condition} order by date,act_symbol limit 1000 offset {offset}"
                )
            )
        if len(rows) != count:
            raise ValueError("Incomplete market session")
    if len(rows) != len({(r["date"], r["act_symbol"]) for r in rows}):
        raise ValueError("Duplicate data")
    bad = 0
    days = set()
    symbols = set()
    for r in rows:
        try:
            lo, op, cl, hi = (float(r[k]) for k in ("low", "open", "close", "high"))
            valid = (
                all(math.isfinite(n) for n in (lo, op, cl, hi))
                and 0 < lo <= min(op, cl) <= max(op, cl) <= hi
                and int(r["volume"]) >= 0
            )
        except (ValueError, TypeError):
            valid = False
        if valid:
            days.add(r["date"])
            symbols.add(r["act_symbol"])
        else:
            bad += 1
    if days != {label[-10:]} or bad:
        raise ValueError("Invalid prices or date in session")
    raw = (
        content
        if len(paths) == 1
        else gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0)
    )
    return dict(
        label=label,
        rows=len(rows),
        valid_dates=len(days),
        valid_tickers=len(symbols),
        invalid_rows=bad,
        first=min(days),
        last=max(days),
        file=immutable_save(DEST, label, raw, "json.gz"),
    )


def main():
    part = fetch("market-" + LAST, "date='" + LAST + "'")
    record = dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), source=BASE, parts=[part])
    immutable_save(DEST, "receipt", json.dumps(record, indent=2).encode(), "json")
    print(part["valid_tickers"], part["last"])


if __name__ == "__main__":
    main()
