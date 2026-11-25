"""Collect weekly CFTC futures-only market aggregates for the ten research roots."""
import csv
from datetime import date, datetime, timezone
import io
import json
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request

MARKETS = {"ES":"13874A", "NQ":"209742", "RTY":"239742", "ZT":"042601",
           "ZF":"044601", "ZN":"043602", "ZB":"020601", "CL":"067651",
           "GC":"088691", "6S":"092741"}


def main():
    cutoff = date.today().isoformat()
    base = ROOT / "data/raw/public_universe" / cutoff
    fields = ("cftc_contract_market_code", "market_and_exchange_names", "report_date_as_yyyy_mm_dd",
              "open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all")
    codes = ",".join(f"'{v}'" for v in MARKETS.values())
    query = {"$select": ",".join(fields), "$where": f"cftc_contract_market_code in ({codes}) AND report_date_as_yyyy_mm_dd between '1998-01-01T00:00:00' and '{cutoff}T00:00:00'",
             "$order": "cftc_contract_market_code,report_date_as_yyyy_mm_dd", "$limit": 50000}
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.csv?" + urlencode(query)
    raw = request(url)
    records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    days = {code: set() for code in MARKETS.values()}
    for row in records:
        seen = days[row[fields[0]]]
        day = date.fromisoformat(row[fields[2]][:10]).isoformat()
        if day in seen or day > cutoff or int(row["open_interest_all"]) < 0:
            raise ValueError("Invalid COT market observation")
        seen.add(day)
    if len(records) >= 50000 or not all(days.values()):
        raise ValueError("Incomplete COT download")
    coverage = {root: [len(days[code]), min(days[code]), max(days[code])] for root, code in MARKETS.items()}
    result = dict(dataset="cftc_legacy_futures_only", source=url, rows=len(records),
                  first_record=min(min(d) for d in days.values()), last_record=max(max(d) for d in days.values()),
                  kind="weekly market-level positioning; all maturities aggregated", coverage=coverage,
                  files=[immutable_save(base, "cftc-weekly", raw, "csv")], status="downloaded_schema_checked_not_normalized")
    immutable_save(base, "receipt", json.dumps(dict(schema="public-source-receipt-v1",
                   acquired_at_utc=datetime.now(timezone.utc).isoformat(), datasets=[result]), indent=2).encode(), "json")
    print(coverage)


if __name__ == "__main__":
    main()
