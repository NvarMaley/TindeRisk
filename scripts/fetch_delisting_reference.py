"""Download a full public delisting table, then identify research leads locally by ticker."""

import csv
from datetime import date, datetime, timezone
import gzip
import io
import json
import re

from bs4 import BeautifulSoup
from audit_research_extensions import check, latest
from fetch_public_universe_data import ROOT, immutable_save, request

URL = "https://www.quotelinks.com/delisted.html"


def main():
    html = BeautifulSoup(request(URL), "html.parser")
    rows = []
    for table in html.find_all("table"):
        heading = table.find_previous(["h2", "h3"])
        match = (
            re.fullmatch(r"Stocks delisted in (20\d\d)", heading.get_text(" ", strip=True))
            if heading
            else None
        )
        if not match:
            continue
        for tr in table.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
            if not cells:
                continue
            ticker, company, sector, close, day, reason = cells
            stamp = datetime.strptime(day + " " + match[1], "%b %d %Y").date()
            if stamp <= date.today():
                rows.append((str(stamp), ticker, company, sector, close, reason))
    dest = ROOT / "data/raw/delisting_reference"
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["last_trade", "symbol", "company", "sector", "vendor_final_close", "vendor_reason"]
    )
    writer.writerows(rows)
    file = immutable_save(
        dest, "public-events", gzip.compress(out.getvalue().encode(), mtime=0), "csv.gz"
    )
    _, market = latest(ROOT / "data/raw/public_market_history", "*/receipt-*.json")
    local = ROOT / "data/processed/universe/market_matches"
    with gzip.open(check(local, market["local_match_file"]), "rt") as f:
        partial = {
            r["snapshot_ticker"]: r["local_permno"]
            for r in csv.DictReader(f)
            if int(r["sessions"]) < market["expected_days"]
            and r["match_status"] == "unambiguous_snapshot_ticker"
        }
    leads = [
        (partial[r[1]], *r)
        for r in rows
        if market["first"] <= r[0] <= market["last"] and r[1] in partial
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "local_permno",
            "last_trade",
            "symbol",
            "company",
            "sector",
            "vendor_final_close",
            "vendor_reason",
        ]
    )
    writer.writerows(leads)
    private = immutable_save(
        local, "public-delist-leads", gzip.compress(out.getvalue().encode(), mtime=0), "csv.gz"
    )
    receipt = dict(
        source=URL,
        rows=len(rows),
        file=file,
        local_leads_file=private,
        candidate_leads=len({r[0] for r in leads}),
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    immutable_save(dest, "receipt", json.dumps(receipt, indent=2).encode(), "json")
    print(receipt["rows"], receipt["candidate_leads"])


if __name__ == "__main__":
    main()
