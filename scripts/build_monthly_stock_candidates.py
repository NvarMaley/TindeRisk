"""Rank US common-stock candidates at each observed month end for subsequent decisions."""
import csv
from datetime import date
import gzip
import json
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder, = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "new data")
    source = folder / "data_plus/raw/wrds/crsp_msf.csv"
    stamp = source.stat()
    dest = ROOT / "data/processed/universe"
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        db = sqlite3.connect(Path(tmp) / "rank.db")
        db.execute("CREATE TABLE candidates(day TEXT, permno INTEGER, low REAL, high REAL, PRIMARY KEY(day,permno)) WITHOUT ROWID")
        def observations():
            with source.open(newline="") as stream:
                for r in csv.DictReader(stream):
                    if (r["SecurityType"], r["SecuritySubType"], r["ShareType"], r["USIncFlg"]) != ("EQTY", "COM", "NS", "Y"):
                        continue
                    if r["IssuerType"] not in ("CORP", "ACOR") or r["PrimaryExch"] not in ("N", "A", "Q"):
                        continue
                    day = r["MthCalDt"]
                    if r["TradingStatusFlg"] != "A" or r["ConditionalType"] != "RW":
                        continue
                    if not r["SecInfoStartDt"] <= day <= r["SecInfoEndDt"] or not r["SecurityBegDt"] <= day <= r["SecurityEndDt"]:
                        continue
                    try:
                        cap = float(r["MthCap"])
                    except ValueError:
                        continue
                    if 0 < cap < float("inf"):
                        yield day, int(r["PERMNO"]), cap, cap
        db.executemany("""INSERT INTO candidates VALUES(?,?,?,?) ON CONFLICT(day,permno)
                          DO UPDATE SET low=min(low,excluded.low), high=max(high,excluded.high)""", observations())
        rows = db.execute("""SELECT day, permno, rank FROM (
            SELECT day, permno, row_number() OVER (PARTITION BY day ORDER BY high DESC, permno) AS rank
            FROM candidates WHERE low=high) WHERE rank<=1000 ORDER BY day,rank""")
        counts = {}
        output = Path(tmp) / "monthly_stock_candidates.csv.gz"
        with gzip.open(output, "wt", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["ranking_date", "permno", "rank"])
            for day, permno, rank in rows:
                writer.writerow([day, permno, rank])
                counts[day] = rank
        db.close()
        if not counts or stamp.st_mtime_ns != source.stat().st_mtime_ns:
            raise ValueError("Missing rankings or source changed")
        meta = dict(audited_on=date.today().isoformat(), months=len(counts), first=min(counts),
                    last=max(counts), min_candidates=min(counts.values()), rows=sum(counts.values()),
                    source_size=stamp.st_size, source_mtime_ns=stamp.st_mtime_ns)
        output.replace(dest / output.name)
        manifest = Path(tmp) / "monthly_stock_candidates.json"
        manifest.write_text(json.dumps(meta, indent=2))
        manifest.replace(dest / manifest.name)
        print(meta)


if __name__ == "__main__":
    main()
