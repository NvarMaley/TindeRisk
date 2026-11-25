"""Compare the private stock cohort with public issuer and market references entirely offline."""

import csv
import gzip
import io
import json
from datetime import datetime, timezone

import duckdb
from audit_research_extensions import check, latest
from fetch_public_universe_data import ROOT, immutable_save


def main():
    raw = ROOT / "data/raw"
    derived = ROOT / "data/processed/universe"
    folder, prices = latest(raw / "public_market_history", "*/receipt-*.json")
    bars = check(folder, prices["file"])
    local_match = check(derived / "market_matches", prices["local_match_file"])
    folder, refs = latest(raw / "listing_reference")
    public = check(folder, refs["references"]["tickers.parquet"]["file"])
    (folder,) = (p for p in (ROOT / "data").iterdir() if p.name.strip() == "telecharger")
    links = json.loads((derived / "wrds_delivery.json").read_text())["tables"]["links"]
    cohort_date = json.loads((derived / "crsp_monthly_audit.json").read_text())["snapshot_date"]
    db = duckdb.connect()
    db.execute(
        "create temp table cohort as select * from read_csv(?,all_varchar=true)", [str(local_match)]
    )
    db.execute(
        """create temp table identities as select lpermno,min(try_cast(cik as bigint)) cik
               from read_csv(?,all_varchar=true) where linktype in ('LU','LC') and linkprim in ('P','C')
               and cast(? as date) between try_cast(linkdt as date) and coalesce(try_cast(linkenddt as date),date '9999-12-31')
               group by lpermno having count(distinct try_cast(cik as bigint))=1""",
        [str(folder / links["file"]), cohort_date],
    )
    db.execute(
        "create temp table aliases as select distinct cik,ticker from read_parquet(?)",
        [str(public)],
    )
    db.execute(
        "create temp table seen as select distinct act_symbol from read_parquet(?)", [str(bars)]
    )
    result = db.execute("""select c.local_permno, c.snapshot_ticker,c.sessions,i.cik,
                      max(a.ticker=c.snapshot_ticker) as issuer_supports_ticker,
                      list(distinct a.ticker order by a.ticker) filter(where s.act_symbol is not null and a.ticker<>c.snapshot_ticker) other_observed_issuer_tickers
                      from cohort c left join identities i on c.local_permno=i.lpermno
                      left join aliases a using(cik) left join seen s on a.ticker=s.act_symbol
                      group by c.local_permno,c.snapshot_ticker,c.sessions,i.cik order by c.local_permno""")
    values = result.fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([v[0] for v in result.description])
    writer.writerows(values)
    dest = derived / "market_matches"
    file = immutable_save(
        dest, "issuer-crosscheck", gzip.compress(out.getvalue().encode(), mtime=0), "csv.gz"
    )
    report = dict(
        cohort=len(values),
        unique_cik=sum(r[3] is not None for r in values),
        unchanged_ticker_confirmed=sum(r[4] is True and int(r[2]) > 0 for r in values),
        no_observed_match_with_alternate=sum(int(r[2]) == 0 and bool(r[5]) for r in values),
        file=file,
        source_snapshot="2026-09-30",
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    index_folder, index_receipt = latest(raw / "sec_filing_index")
    if index_receipt:
        index = index_folder / ("filings-" + index_receipt["sha256"][:16] + ".parquet")
        leads = db.execute(
            """select distinct c.local_permno,i.cik,f.accessionNumber,f.filingDate,f.form
                          from cohort c join identities i on c.local_permno=i.lpermno
                          join read_parquet(?) f on f.cik=i.cik
                          where try_cast(c.sessions as integer)<? and f.form in ('25','25-NSE','25/A','25-NSE/A')
                          and f.filingDate between cast(? as date) and cast(? as date)
                          order by c.local_permno,f.filingDate""",
            [str(index), prices["expected_days"], prices["first"], prices["last"]],
        )
        rows = leads.fetchall()
        payload = io.StringIO()
        writer = csv.writer(payload)
        writer.writerow([x[0] for x in leads.description])
        writer.writerows(rows)
        report["issuer_delisting_leads"] = len({r[0] for r in rows})
        report["lead_file"] = immutable_save(
            dest, "issuer-form25", gzip.compress(payload.getvalue().encode(), mtime=0), "csv.gz"
        )
    immutable_save(dest, "identity", json.dumps(report, indent=2).encode(), "json")
    print({k: v for k, v in report.items() if k != "file"})


if __name__ == "__main__":
    main()
