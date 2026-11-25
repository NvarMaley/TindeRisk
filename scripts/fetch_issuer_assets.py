"""Extract dated share-class or fund net assets from the eight remaining issuer factsheets."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import json
import re
import subprocess

from fetch_public_universe_data import ROOT, request, immutable_save

DEST = ROOT / "data/raw/issuer_assets"
VANGUARD = "https://workplace.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0986.pdf"


def get(row):
    ticker = row["ticker"]
    url = VANGUARD if ticker == "VNQ" else row["source"]
    raw = request(url)
    if not raw.startswith(b"%PDF-"):
        raise ValueError("Issuer document format mismatch")
    file = immutable_save(DEST, ticker, raw, "pdf")
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(DEST / file["file"]), "-"], text=True
    )
    if not re.search(r"\b" + ticker + r"\b", text):
        raise ValueError("Factsheet ticker mismatch")
    label = (
        r"ETF total net assets\s*\$([\d,.]+) million"
        if ticker == "VNQ"
        else r"Net Assets of Fund \(M\)\s*:\s*\$([\d,.]+)"
    )
    value = re.search(label, text)
    day = re.search(r"(?:fact sheet as of|as of) ([A-Za-z]+ \d{1,2}, 20\d{2})", text, re.I)
    if not day or not value:
        raise ValueError("Factsheet amount or date missing")
    return dict(
        ticker=ticker,
        source=url,
        as_of=datetime.strptime(day[1], "%B %d, %Y").date().isoformat(),
        net_assets_usd=str(Decimal(value[1].replace(",", "")) * 1000000),
        file=file,
    )


def main():
    funds = json.loads((ROOT / "configs/universe_catalog.json").read_text())["instruments"]
    with ThreadPoolExecutor(3) as pool:
        rows = list(
            pool.map(get, [r for r in funds if r["sponsor"] == "iShares" or r["ticker"] == "VNQ"])
        )
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), funds=rows), indent=2
        ).encode(),
        "json",
    )
    print([(r["ticker"], r["as_of"]) for r in rows])


if __name__ == "__main__":
    main()
