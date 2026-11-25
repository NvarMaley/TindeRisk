"""Measure last-20-session ETF turnover and compare contemporaneous issuer NAV and assets."""

import csv
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import io
import json

import duckdb
from audit_research_extensions import check, latest
from fetch_issuer_holdings import bil_rows
from fetch_public_universe_data import ROOT, immutable_save


def main():
    raw = ROOT / "data/raw"
    folder, bars = latest(raw / "public_market_history", "*/receipt-*.json")
    source = check(folder, bars["file"])
    tickers = sorted(bars["etf_days"])
    with duckdb.connect() as db:
        quote = db.execute(
            """with daily as (
            select *,row_number() over(partition by act_symbol order by date desc) as recency
            from read_parquet(?) where act_symbol in (select unnest(?)) and volume>=0 and close>0)
            select act_symbol,count(*),arg_max(close,date),avg(close*volume),max(date)
            from daily where recency<=20 group by act_symbol""",
            [str(source), tickers],
        ).fetchall()
    folder, nav = latest(raw / "issuer_nav")
    official = {}
    for fund in nav["funds"]:
        rows = bil_rows(check(folder, fund["file"]).read_bytes())
        for row in rows:
            if len(row) < 4 or not row[0]:
                continue
            try:
                day = datetime.strptime(row[0], "%d-%b-%Y").date().isoformat()
            except ValueError:
                continue
            if day == bars["last"]:
                official[fund["ticker"]] = (Decimal(row[1]), Decimal(row[3]))
                break
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "ticker",
            "as_of",
            "sessions",
            "close",
            "average_close_times_volume_usd",
            "nav",
            "net_assets_usd",
            "close_to_nav_pct",
        ]
    )
    above = assets = 0
    deviations = []
    for ticker, n, price, turnover, day in sorted(quote):
        if n != 20 or str(day) != bars["last"]:
            raise ValueError("Incomplete last-20-session panel")
        nav_price, aum = official.get(ticker, (None, None))
        gap = None if nav_price is None else (Decimal(str(price)) / nav_price - 1) * 100
        above += turnover >= 1000000
        assets += aum is not None and aum >= 100000000
        if gap is not None:
            deviations.append(abs(gap))
        writer.writerow([ticker, day, n, price, turnover, nav_price, aum, gap])
    dest = ROOT / "data/processed/universe/etf_liquidity"
    data = immutable_save(
        dest, "liquidity", gzip.compress(out.getvalue().encode(), mtime=0), "csv.gz"
    )
    record = dict(
        funds=len(quote),
        as_of=bars["last"],
        window_sessions=20,
        above_turnover_proxy=above,
        matched_issuer_nav=len(official),
        above_aum=assets,
        max_abs_nav_gap_pct=str(max(deviations)),
        file=data,
        acquired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    immutable_save(dest, "receipt", json.dumps(record, indent=2).encode(), "json")
    print({k: v for k, v in record.items() if k != "file"})


if __name__ == "__main__":
    main()
