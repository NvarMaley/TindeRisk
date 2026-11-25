"""Download BTC and ETH spot candles from Coinbase, tracking gaps on a seven-day UTC calendar."""

import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import io
import json
import math
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request

DEST = ROOT / "data/raw/crypto_bars"


def fetch(product, first):
    source = f"https://api.exchange.coinbase.com/products/{product}/candles"
    stop = datetime.now(timezone.utc).date()
    start = first
    dates = {}
    gaps = []
    while start < stop:
        end = min(start + timedelta(days=280), stop)
        query = urlencode(
            dict(
                granularity=86400,
                start=start.isoformat() + "T00:00:00Z",
                end=end.isoformat() + "T00:00:00Z",
            )
        )
        batch = json.loads(request(source + "?" + query))
        if not isinstance(batch, list):
            raise ValueError("Unexpected Coinbase response")
        for stamp, low, high, opening, close, volume in batch:
            day = datetime.fromtimestamp(stamp, timezone.utc).date()
            if day < start or day >= end:
                continue
            if (
                stamp % 86400
                or not all(math.isfinite(v) for v in (low, high, opening, close, volume))
                or not 0 < low <= min(opening, close) <= max(opening, close) <= high
                or volume < 0
                or day in dates
            ):
                raise ValueError(f"Invalid daily candle for {day}")
            dates[day] = (opening, high, low, close, volume)
        start = end
    if not dates:
        raise ValueError("No spot candles returned")
    for i in range((stop - min(dates)).days):
        day = min(dates) + timedelta(days=i)
        if day not in dates:
            gaps.append(str(day))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["utc_day", "open", "high", "low", "close", "base_volume"])
    writer.writerows((day, *values) for day, values in sorted(dates.items()))
    return dict(
        product=product,
        source=source,
        days=len(dates),
        first=str(min(dates)),
        last=str(max(dates)),
        missing_days=gaps,
        file=immutable_save(
            DEST, product, gzip.compress(output.getvalue().encode(), mtime=0), "csv.gz"
        ),
    )


def main():
    parts = [
        fetch(product, first)
        for product, first in (("BTC-USD", date(2014, 12, 1)), ("ETH-USD", date(2016, 5, 1)))
    ]
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), products=parts), indent=2
        ).encode(),
        "json",
    )
    print([(p["product"], p["days"], p["last"], len(p["missing_days"])) for p in parts])


if __name__ == "__main__":
    main()
