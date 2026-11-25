"""Download dated public fund fee readings and preserve their sources, precision and units."""

import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import gzip
import io
import json
import re
import subprocess

from fetch_public_universe_data import ROOT, immutable_save, request

BASE = "https://expenseratiohistory.com/data/"
DEST = ROOT / "data/raw/fund_fees"


def main():
    tickers = {
        r["ticker"]
        for r in json.loads((ROOT / "configs/universe_catalog.json").read_text())["instruments"]
    }
    tables = {}
    for name, day_key, fee_key in (
        ("fund-fees", "date", "expense_ratio_pct"),
        ("fee-changes", "effective_date", "new_expense_ratio_pct"),
    ):
        raw = request(BASE + name + ".csv")
        source = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows = []
        for row in source:
            if row["ticker"] not in tickers:
                continue
            day = date.fromisoformat(row[day_key])
            if day > date.today() or not row["source_url"] or not Decimal(row[fee_key]).is_finite():
                continue
            rows.append(row)
        if not rows:
            raise ValueError("No matching dated fee records")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=source.fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        tables[name] = dict(
            source=BASE + name + ".csv",
            rows=len(rows),
            funds=len({r["ticker"] for r in rows}),
            first=min(r[day_key] for r in rows),
            last=max(r[day_key] for r in rows),
            file=immutable_save(
                DEST, name, gzip.compress(output.getvalue().encode(), mtime=0), "csv.gz"
            ),
        )
    url = "https://www.ssga.com/library-content/products/factsheets/etfs/us/factsheet-us-en-mdy.pdf"
    file = immutable_save(DEST, "MDY-factsheet", request(url), "pdf")
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(DEST / file["file"]), "-"], text=True
    )
    fee = re.search(r"Gross Expense Ratio \( ?% ?\)\s+([0-9.]+)", text)
    stamp = re.search(r"As of (\d{2}/\d{2}/\d{4})", text)
    if not fee or not stamp or "MIDCAP 400" not in text or "MDY" not in text:
        raise ValueError("MDY factsheet identity or fee missing")
    tables["MDY"] = dict(
        source=url,
        fee_pct=fee[1],
        basis="gross",
        as_of=datetime.strptime(stamp[1], "%m/%d/%Y").date().isoformat(),
        file=file,
    )
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(
                credit="Expense Ratio History",
                source=BASE,
                fee_table_license="CC BY 4.0",
                tables=tables,
                acquired_at_utc=datetime.now(timezone.utc).isoformat(),
            ),
            indent=2,
        ).encode(),
        "json",
    )
    print({k: v.get("funds", 1) for k, v in tables.items()})


if __name__ == "__main__":
    main()
