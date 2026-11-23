"""Build a monthly CHF catalogue from a pinned local market snapshot."""

import argparse
import csv
from datetime import date, datetime
from hashlib import sha256
import io
import json
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


def read_fx(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["observation_date", "DEXSZUS"]:
        raise ValueError("Unexpected DEXSZUS diagram")
    points = {}
    for row in reader:
        day = date.fromisoformat(row["observation_date"])
        if day in points or None in row or row["DEXSZUS"] is None:
            raise ValueError(f"Currency line invalidated on {day}")
        points[day] = float(row["DEXSZUS"]) if row["DEXSZUS"] else None
    return points


def read_prices(raw, symbol):
    envelope = json.loads(raw)
    payload = envelope["payload"]
    if sha256(payload.encode()).hexdigest() != envelope["sha256"]:
        raise ValueError(f"Modified source load for {symbol}")
    chart = json.loads(payload)["chart"]["result"][0]
    meta = chart["meta"]
    if meta["symbol"] != symbol or meta["currency"] != "USD":
        raise ValueError(f"Identity or unexpected currency for {symbol}")
    points = {}
    for timestamp, price in zip(chart["timestamp"], chart["indicators"]["adjclose"][0]["adjclose"], strict=True):
        day = datetime.fromtimestamp(timestamp, ZoneInfo(meta["exchangeTimezoneName"])).date()
        if day in points or price is None:
            raise ValueError(f"Missing or duplicated prices for {symbol} le {day}")
        points[day] = price
    return points


def monthly_returns(prices, fx):
    """Require adjacent month ends, both with same-day FX. Exclude the terminal month."""
    ends = {}
    for day in sorted(prices):
        ends[day.year * 12 + day.month] = day
    terminal = max(ends)
    rows = {}
    for month, day in ends.items():
        if month == terminal or month - 1 not in ends:
            continue
        previous = ends[month - 1]
        if fx.get(day) is None or fx.get(previous) is None:
            continue
        rows[day] = prices[day] * fx[day] / (prices[previous] * fx[previous]) - 1
    return rows


def build(lock, raw_dir):
    fx = {}
    prices = {}
    stats = {}
    for source in lock["sources"]:
        symbol = source["series"]
        raw = (raw_dir / source["file"]).read_bytes()
        if sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Checksum mismatch for {symbol}. Import suspended, vintage to qualify.")
        if symbol in stats:
            raise ValueError(f"Double series for {symbol}")
        if symbol == "DEXSZUS":
            fx = points = read_fx(raw)
        else:
            prices[symbol] = points = read_prices(raw, symbol)
        if not points or any(not isfinite(v) or v <= 0 for v in points.values() if v is not None):
            raise ValueError(f"Empty series or invalid value for {symbol}")
        valid = [d for d, v in points.items() if v is not None]
        stats[symbol] = dict(rows=len(points), valid=len(valid), first=min(valid).isoformat(), last=max(valid).isoformat())

    if not prices or not fx:
        raise ValueError("Prices and exchange rates are necessary")
    records = []
    dates_by_asset = []
    for symbol, points in sorted(prices.items()):
        returns = monthly_returns(points, fx)
        if not returns:
            raise ValueError(f"No months can be exploited for {symbol}")
        dates_by_asset.append(set(returns))
        for day, value in sorted(returns.items()):
            records.append((day, symbol, lock["classes"][symbol], "instrument", value, lock["version"]))
    common = sorted(set.intersection(*dates_by_asset))
    if not common:
        raise ValueError("No date common to the funds")
    summary = dict(version=lock["version"], sources=stats, rows=len(records),
                   common_month_ends=[day.isoformat() for day in common])
    return records, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("config/import-2026-11-23.json"))
    parser.add_argument("--raw", type=Path, default=Path("data/local/1.3/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/local/1.3"))
    args = parser.parse_args()
    lock = json.loads(args.lock.read_bytes())
    rows, summary = build(lock, args.raw)
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / lock["version"]
    with TemporaryDirectory(dir=args.output) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir()
        with (stage / "returns.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(("date", "asset_id", "asset_class", "role", "return_chf", "source"))
            writer.writerows(rows)
        summary["catalogue_sha256"] = sha256((stage / "returns.csv").read_bytes()).hexdigest()
        (stage / "coverage.json").write_text(json.dumps(summary, indent=2) + "\n")
        if target.exists():
            for name in ("coverage.json", "returns.csv"):
                if (stage / name).read_bytes() != (target / name).read_bytes():
                    raise ValueError(f"Different result of the existing vintage in {target}")
        else:
            stage.rename(target)
    print(f"{len(rows)} returns in {target}, {len(summary['common_month_ends'])} common months")


if __name__ == "__main__":
    main()
