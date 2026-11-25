"""Inventory local WRDS exports by schema. Raw observations stay outside Git."""
import csv
from datetime import date
import gzip
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
# Key on distinctive columns rather than provider-generated filenames.
SCHEMAS = {
    "dlycapflg": ("daily_supplement", "dlycaldt"),
    "shrstartdt": ("shares", "shrstartdt"),
    "disseqnbr": ("distributions", "disexdt"),
    "deldtprc": ("delistings", "delistingdt"),
    "securityhdrflg": ("security_header", "secinfostartdt"),
    "hdrprimaryexch": ("names_history", "secinfostartdt"),
    "dlycaldt": ("daily_index", "dlycaldt"),
    "mthcaldt": ("monthly_index", "mthcaldt"),
    "curcdq": ("quarterly", "datadate"),
    "prcc_f": ("annual", "datadate"),
    "linkprim": ("links", "linkdt"),
}


def main():
    folder, = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "telecharger")
    today = date.today().isoformat()
    tables = {}
    for path in sorted(folder.glob("*.csv*")):
        stamp = path.stat()
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            columns = [name.lower() for name in next(reader)]
            matches = [v for k, v in SCHEMAS.items() if k in columns]
            if not matches:
                continue
            table, date_col = matches[0]
            if table in tables:
                raise ValueError(f"Ambiguous export for {table}")
            idx = columns.index(date_col)
            volume = columns.index("dlyvol") if "dlyvol" in columns else None
            rdq = columns.index("rdq") if "rdq" in columns else None
            count = future = populated = announced = 0
            first = last = None
            for row in reader:
                if len(row) != len(columns):
                    raise ValueError(f"Unexpected row width in {table}")
                count += 1
                day = row[idx]
                if day and day != ".":
                    first = day if first is None or day < first else first
                    last = day if last is None or day > last else last
                    future += day > today
                if volume is not None and row[volume] not in ("", "."):
                    populated += 1
                if rdq is not None and row[rdq] not in ("", ".") and row[rdq] <= today:
                    announced += 1
        if (path.stat().st_size, path.stat().st_mtime_ns) != (stamp.st_size, stamp.st_mtime_ns):
            raise ValueError("Source changed during scan")
        tables[table] = dict(file=path.name, rows=count, first=first, last=last,
                             future_dated=future, columns=columns, size=stamp.st_size,
                             mtime_ns=stamp.st_mtime_ns)
        if volume is not None:
            tables[table]["populated_volume"] = populated
        if rdq is not None:
            tables[table]["rdq_by_audit_date"] = announced
        print(table, count, first, last, flush=True)
    dest = ROOT / "data/processed/universe/wrds_delivery.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=dest.parent, delete=False) as tmp:
        json.dump({"audited_on": today, "tables": tables}, tmp, indent=2)
    Path(tmp.name).replace(dest)


if __name__ == "__main__":
    main()
