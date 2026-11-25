"""Verify local receipts and record historical coverage, preserving source boundaries."""
from datetime import date
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import tempfile

from fetch_public_universe_data import ROOT


def verified(folder, entry):
    name = entry["file"]
    if Path(name).name != name:
        raise ValueError("Invalid receipt path")
    path = folder / name
    with path.open("rb") as s:
        if hashlib.file_digest(s, "sha256").hexdigest() != entry["sha256"]:
            raise ValueError("Source fingerprint mismatch")
    return path


def main():
    raw = ROOT / "data/raw"
    tips = sorted((raw / "tips_ratios").glob("*/receipt-*.json"))[-1]
    ratios = json.loads(tips.read_text())["issues"]
    ratios = [r for r in ratios if "file" in r]
    for r in ratios:
        verified(tips.parent, r["file"])
    statement = sorted((raw / "monthly_treasury_debt").glob("*/receipt-*.json"))[-1]
    pages = json.loads(statement.read_text())["pages"]
    outstanding = {}
    classes = {"Bills Maturity Value","Notes","Bonds","Inflation-Protected Securities"}
    for page in pages:
        with gzip.open(verified(statement.parent, page["file"])) as s:
            for row in json.load(s)["data"]:
                day, cusip, amount = row["record_date"], row["security_class2_desc"], row["outstanding_amt"]
                if row["security_class1_desc"] not in classes or not re.fullmatch("[A-Z0-9]{9}",cusip):
                    continue
                if amount in ("", "null", None) or Decimal(amount) <= 0:
                    continue
                outstanding.setdefault(day,set()).add(cusip)
    archives = []
    for receipt in sorted((raw / "treasury_archive").glob("receipt-*.json")):
        r = json.loads(receipt.read_text())
        verified(receipt.parent, r["file"])
        archives.append({k:r[k] for k in ("source","days","first","last")})
    result = dict(audited_on=date.today().isoformat(), tips_issues=len(ratios),
                  tips_days_by_issue=sum(r["rows"] for r in ratios), monthly_statements=len(outstanding),
                  latest_statement=max(outstanding), latest_positive_issues=len(outstanding[max(outstanding)]),
                  archives=archives)
    dest = ROOT / "data/processed/universe/treasury_supplements.json"
    with tempfile.NamedTemporaryFile(mode="w",dir=dest.parent,delete=False) as s:
        json.dump(result,s,indent=2)
    Path(s.name).replace(dest)
    print(result)


if __name__ == "__main__":
    main()
