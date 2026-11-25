"""Archive SOFR and the accrued SOFR index, preserving their units and observation dates."""

import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import io
import json
from urllib.parse import urlencode

from fetch_public_universe_data import ROOT, immutable_save, request


def main():
    dest = ROOT / "data/raw/cash_reference"
    rows = []
    for symbol in ("SOFR", "SOFRINDEX"):
        source = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urlencode(
            {"id": symbol, "cosd": "2018-04-02", "coed": date.today().isoformat()}
        )
        raw = request(source)
        observations = {}
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
            if row[symbol] in ("", "."):
                continue
            day = date.fromisoformat(row["observation_date"])
            value = Decimal(row[symbol])
            if (
                day in observations
                or not value.is_finite()
                or (symbol == "SOFRINDEX" and value <= 0)
            ):
                raise ValueError("Invalid or duplicate SOFR observation")
            observations[day] = value
        rows.append(
            dict(
                symbol=symbol,
                source=source,
                days=len(observations),
                first=str(min(observations)),
                last=str(max(observations)),
                unit="index level" if symbol == "SOFRINDEX" else "annualized percent",
                file=immutable_save(dest, symbol, raw, "csv"),
            )
        )
    immutable_save(
        dest,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), series=rows), indent=2
        ).encode(),
        "json",
    )
    print([(r["symbol"], r["days"], r["last"]) for r in rows])


if __name__ == "__main__":
    main()
