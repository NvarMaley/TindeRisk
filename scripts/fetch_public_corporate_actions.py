"""Archive the full public split and cash distribution tables without sending local identifiers."""

import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import gzip
import io
import json

from fetch_public_market_bars import REVISION
from fetch_public_universe_data import ROOT, immutable_save, request

BASE = f"https://www.dolthub.com/csv/post-no-preference/stocks/{REVISION}"


def main():
    folder = ROOT / "data/raw/public_actions" / REVISION
    parts = {}
    for table, fields in (("split", ("to_factor", "for_factor")), ("dividend", ("amount",))):
        raw = request(f"{BASE}/{table}")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if reader.fieldnames != ["act_symbol", "ex_date", *fields]:
            raise ValueError(f"Unexpected {table} schema")
        dates = []
        invalid = 0
        for row in reader:
            day = date.fromisoformat(row["ex_date"])
            amounts = [Decimal(row[k]) for k in fields]
            if not row["act_symbol"] or any(not n.is_finite() for n in amounts):
                raise ValueError(f"Invalid {table} record")
            if table == "split" and min(amounts) <= 0:
                invalid += 1
            dates.append(day)
        parts[table] = dict(
            rows=len(dates),
            invalid_factors=invalid,
            first=str(min(dates)),
            last=str(max(dates)),
            file=immutable_save(folder, table, gzip.compress(raw, mtime=0), "csv.gz"),
        )
    immutable_save(
        folder,
        "receipt",
        json.dumps(
            dict(
                source=BASE,
                revision=REVISION,
                acquired_at_utc=datetime.now(timezone.utc).isoformat(),
                tables=parts,
            ),
            indent=2,
        ).encode(),
        "json",
    )
    print({k: (v["rows"], v["last"]) for k, v in parts.items()})


if __name__ == "__main__":
    main()
