"""Compare official valuation observations to the issue master and nominal curve calendar."""

import csv
from datetime import date
import json
from pathlib import Path
import tempfile

from audit_research_extensions import check
from fetch_public_universe_data import ROOT

DERIVED = ROOT / "data/processed/universe"


def main():
    master = {
        r["cusip"]: r for r in json.loads((DERIVED / "treasury_identity.json").read_text())["rows"]
    }
    curve = sorted((ROOT / "data/raw/public_universe").glob("*/fred-DGS10-*.csv"))[-1]
    with curve.open() as stream:
        expected = sorted(
            r["observation_date"]
            for r in csv.DictReader(stream)
            if r["DGS10"] not in ("", ".") and r["observation_date"] >= "2008-09-02"
        )
    ends = {day[:7]: day for day in expected if day[:7] < date.today().isoformat()[:7]}
    days = set()
    counts = {}
    tail = {day for day in expected if day > "2024-11-22"}
    for folder in (ROOT / "data/raw/fedinvest").iterdir():
        receipts = list(folder.glob("receipt-*.json"))
        if not receipts:
            continue
        receipt = json.loads(max(receipts, key=lambda p: p.stat().st_mtime).read_text())
        day = receipt["date"]
        with check(folder, receipt["file"]).open() as stream:
            for row in csv.DictReader(stream):
                security = master.get(row["CUSIP"])
                if (
                    not security
                    or not security["first_observed_issue_date"] <= day <= security["maturity"]
                ):
                    continue
                if row["date"] != day or not row["END OF DAY"] or float(row["END OF DAY"]) <= 0:
                    continue
                days.add(day)
                kind = security["instrument_type"]
                counts[kind] = counts.get(kind, 0) + 1
    result = dict(
        audited_on=date.today().isoformat(),
        days=len(days),
        first=min(days),
        last=max(days),
        matched_positive_marks=counts,
        expected_ends=len(ends),
        observed_ends=len(set(ends.values()) & days),
        expected_recent=len(tail),
        observed_recent=len(tail & days),
        calendar_last=max(expected),
        missing_recent=sorted(tail - days),
        missing_ends=sorted(set(ends.values()) - days),
    )
    with tempfile.NamedTemporaryFile(mode="w", dir=DERIVED, delete=False) as stream:
        json.dump(result, stream, indent=2)
    Path(stream.name).replace(DERIVED / "treasury_sessions.json")
    print({k: v for k, v in result.items() if not k.startswith("missing_")})


if __name__ == "__main__":
    main()
