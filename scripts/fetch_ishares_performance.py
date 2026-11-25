"""Save issuer-reported growth-of-investment and distribution histories separately."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import html
import json
import re

from fetch_public_universe_data import ROOT, request, immutable_save

IDS = {
    "IWD": 239708,
    "IWF": 239706,
    "IWM": 239710,
    "IEF": 239456,
    "SHY": 239452,
    "TLT": 239454,
    "TIP": 239467,
}
DEST = ROOT / "data/raw/issuer_performance"


def get(item):
    ticker, fund = item
    slugs = {
        "IWF": "ishares-russell-1000-growth-etf",
        "IWD": "ishares-russell-1000-value-etf",
        "IWM": "ishares-russell-2000-etf",
        "SHY": "ishares-1-3-year-treasury-bond-etf",
        "IEF": "ishares-7-10-year-treasury-bond-etf",
        "TLT": "ishares-20-year-treasury-bond-etf",
        "TIP": "ishares-tips-bond-etf",
    }
    url = f"https://www.ishares.com/us/products/{fund}/{slugs[ticker]}"
    page = html.unescape(request(url).decode())
    if not re.search(r"\b" + ticker + r"\b", page[:18000]):
        raise ValueError("Issuer page identity mismatch")

    def point(label):
        marker = '{"name":"' + label + '","fullName":"performance.'
        obj = json.JSONDecoder().raw_decode(page[page.index(marker) :])[0]
        return obj

    growth = point("performanceData")
    days = growth["asOfDate"]
    if len(set(days)) != len(days) or len(days) != len(growth["value"]):
        raise ValueError("Malformed issuer series")
    dist = point("distributions")["subContainersByNameMap"]["table"]["dataPointsByNameMap"]
    vals = {k: v["value"] for k, v in dist.items() if isinstance(v.get("value"), list)}
    result = dict(
        growth_of_hypothetical_investment=list(zip(days, growth["value"])), distributions=vals
    )
    compressed = gzip.compress(json.dumps(result).encode(), mtime=0)
    return dict(
        ticker=ticker,
        source=url,
        months=len(days),
        last=str(max(days)),
        distributions=len(vals.get("exDate", [])),
        file=immutable_save(DEST, ticker, compressed, "json.gz"),
    )


def main():
    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {s: pool.submit(get, (s, i)) for s, i in IDS.items()}
        for s, j in jobs.items():
            try:
                rows.append(j.result())
            except (OSError, KeyError, ValueError) as e:
                print(s, str(e), flush=True)
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), funds=rows), indent=2
        ).encode(),
        "json",
    )
    print([(r["ticker"], r["last"], r["distributions"]) for r in rows])


if __name__ == "__main__":
    main()
