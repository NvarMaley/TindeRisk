"""Download issuer NAV, shares and net assets histories, retaining the original workbook."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math

from fetch_issuer_holdings import bil_rows
from fetch_public_universe_data import ROOT, immutable_save, request

TICKERS = "SPY MDY XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY BIL".split()


def fetch(ticker):
    url = (
        "https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-"
        + ticker.lower()
        + ".xlsx"
    )
    raw = request(url)
    rows = bil_rows(raw)
    if ["Ticker Symbol:", ticker] not in rows:
        raise ValueError("Incorrect fund")
    header = next(
        i
        for i, r in enumerate(rows)
        if r[:4] == ["Date", "NAV", "Shares Outstanding", "Total Net Assets"]
    )
    days = set()
    for row in rows[header + 1 :]:
        if len(row) < 4 or not row[0]:
            continue
        try:
            day = datetime.strptime(row[0], "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        if not row[1] or row[1] in ("-", "N/A"):
            continue
        if not math.isfinite(float(row[1])) or float(row[1]) <= 0 or day in days:
            raise ValueError(f"Invalid NAV: {ticker} {day}")
        days.add(day)
    if not days:
        raise ValueError("No dated NAV")
    dest = ROOT / "data/raw/issuer_nav"
    return dict(
        ticker=ticker,
        source=url,
        first=min(days),
        last=max(days),
        dates=len(days),
        file=immutable_save(dest, ticker, raw, "xlsx"),
    )


def main():
    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {t: pool.submit(fetch, t) for t in TICKERS}
        for t, job in jobs.items():
            try:
                rows.append(job.result())
            except (OSError, ValueError, StopIteration) as exc:
                print(t, str(exc), flush=True)
    immutable_save(
        ROOT / "data/raw/issuer_nav",
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), funds=rows), indent=2
        ).encode(),
        "json",
    )
    print([(r["ticker"], r["last"]) for r in rows])


if __name__ == "__main__":
    main()
