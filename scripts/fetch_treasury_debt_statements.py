"""Acquire the marketable-security rows of the official monthly debt statement."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import gzip
import json
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request

URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_3_market"


def main():
    cutoff = date.today().isoformat()
    dest = ROOT / "data/raw/monthly_treasury_debt" / cutoff
    def page(number):
        params = {"sort":"record_date,src_line_nbr", "filter":f"record_date:lte:{cutoff}",
                  "page[size]":5000, "page[number]":number}
        raw = request(URL + "?" + urlencode(params))
        data = json.loads(raw)
        if not all("outstanding_amt" in r and "security_class2_desc" in r and r["record_date"] <= cutoff for r in data["data"]):
            raise ValueError("Invalid debt statement")
        return dict(page=number, rows=len(data["data"]), total=int(data["meta"]["total-count"]),
                    pages=int(data["meta"]["total-pages"]), first=data["data"][0]["record_date"],
                    last=data["data"][-1]["record_date"],
                    file=immutable_save(dest,f"page-{number:03}",gzip.compress(raw,mtime=0),"json.gz"))
    first = page(1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = [first, *pool.map(page, range(2, first["pages"] + 1))]
    if sum(p["rows"] for p in pages) != first["total"] or any(p["total"] != first["total"] for p in pages):
        raise ValueError("Incomplete debt statement")
    immutable_save(dest,"receipt",json.dumps(dict(source=URL,acquired_at_utc=datetime.now(timezone.utc).isoformat(),
                   pages=pages),indent=2).encode(),"json")
    print(first["total"], first["first"], pages[-1]["last"])


if __name__ == "__main__":
    main()
