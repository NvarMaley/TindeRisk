"""Build and reconcile an additive historical panel, keeping CRSP and public returns identifiable."""

import gzip
import hashlib
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import exchange_calendars as xcals
import numpy as np
import pandas as pd

from ..library.sources import checked
from .fetch import (
    ANCHOR,
    BASE,
    CAT,
    DIRECTORY,
    END,
    RAW,
    atomic,
    candidate_symbols,
    cohort,
)
from .identity import references

REPORT = Path("reports/actions-2026")
FIRST = "2025-11-03"
BASELINE = Path("data/local/5/raw/crsp_dsf.csv")
STOP_WORDS = set(
    "inc incorporated corp corporation co company companies plc ltd limited holdings holding the group class common stock shares new of america american and systems technologies international trust bancorp".split()
)
EXPAND = {
    "intl": "international",
    "svcs": "services",
    "natl": "national",
    "hldgs": "holdings",
    "finl": "financial",
    "tech": "technologies",
    "bancshares": "bank",
    "bancorp": "bank",
    "pharmaceuticals": "pharma",
    "laboratories": "labs",
    "bancorporation": "bank",
    "banc": "bank",
    "pharmaceutical": "pharma",
}


def name_tokens(name):
    return {
        EXPAND.get(s, s) for s in re.findall(r"[a-z0-9]+", str(name).lower())
    } - STOP_WORDS


def name_agrees(left, right):
    a, b = name_tokens(left), name_tokens(right)
    if not a or not b:
        return False
    # Preserve distinctive roots such as AIRBNB, and common abbreviations such as PHARM.
    return bool(a & b) or any(
        len(x) >= 4 and len(y) >= 4 and (x.startswith(y) or y.startswith(x))
        for x in a
        for y in b
    )


def read_chart(path, sessions):
    doc = json.loads(gzip.decompress(path.read_bytes()))["chart"]["result"][0]
    meta = doc["meta"]
    if not doc.get("timestamp"):
        raise ValueError("no sessions issued")
    if (
        meta.get("instrumentType") != "EQUITY"
        or meta.get("currency") != "USD"
        or meta.get("exchangeTimezoneName") != "America/New_York"
    ):
        raise ValueError("instrument/currency/place")
    index = (
        pd.to_datetime(doc["timestamp"], unit="s", utc=True)
        .tz_convert("America/New_York")
        .normalize()
        .tz_localize(None)
    )
    bars = doc["indicators"]["quote"][0]
    if index.has_duplicates or not index.isin(sessions).all():
        raise ValueError("calendrier")
    prices = pd.DataFrame(
        dict(
            close=bars["close"],
            volume=bars["volume"],
            adjusted=doc["indicators"]["adjclose"][0]["adjclose"],
        ),
        index=index,
    ).reindex(sessions)
    nonpositive = prices[["close", "adjusted"]].le(0).any(axis=1)
    prices.loc[nonpositive, ["close", "adjusted"]] = np.nan
    prices["usd"] = prices.adjusted.pct_change(fill_method=None)
    events = []
    for kind, items in doc.get("events", {}).items():
        for item in items.values():
            day = (
                pd.Timestamp(item["date"], unit="s", tz="UTC")
                .tz_convert("America/New_York")
                .date()
                .isoformat()
            )
            events.append(
                dict(
                    day=day,
                    kind=kind,
                    amount=item.get("amount"),
                    numerator=item.get("numerator"),
                    denominator=item.get("denominator"),
                )
            )
    return meta, prices, events


def overlap_cache():
    cfg = json.loads(Path("config/faisabilite-5.json").read_bytes())
    digest = cfg["sha256_crsp_dsf"]
    path = BASE / ("overlap-" + digest[:16] + ".parquet")
    if not path.is_file():
        checked(BASELINE, digest)
        db = duckdb.connect()
        query = """SELECT try_cast(PERMNO as integer) permno, CAST(DlyCalDt AS DATE) AS day,
                 max(try_cast(DlyRet AS DOUBLE)) AS ret FROM read_csv(?, all_varchar=true)
                 WHERE DlyCalDt BETWEEN ? AND ? GROUP BY 1,2 HAVING count(*)=1"""
        db.sql(query, params=[str(BASELINE), FIRST, ANCHOR]).write_parquet(
            str(path) + ".part", compression="zstd"
        )
        db.close()
        Path(str(path) + ".part").replace(path)
    data = pd.read_parquet(path)
    data["day"] = pd.to_datetime(data.day)
    return {int(n): g.set_index("day").ret for n, g in data.groupby("permno")}


def inspect_link(row, symbol, meta, prices, events, local, security_symbols):
    if meta.get("symbol") != symbol:
        return "re-directed symbol"
    if security_symbols and symbol not in security_symbols:
        return "class incompatible with CUSIP"
    if symbol not in security_symbols and not name_agrees(
        row.issuer, meta.get("longName") or meta.get("shortName")
    ):
        return "name to be confirmed"
    anchor_price = prices.loc[ANCHOR, "close"]
    factor = np.prod(
        [
            e["numerator"] / e["denominator"]
            for e in events
            if e["kind"] == "splits" and e["day"] > ANCHOR
        ]
    )
    if (
        pd.isna(anchor_price)
        or not np.isfinite(row.price)
        or row.price <= 0
        or abs(anchor_price * factor / row.price - 1) > 0.01
    ):
        return "incompatible connection prices"
    overlap = pd.concat(
        [prices.usd.rename("public"), local.rename("crsp")], axis=1, join="inner"
    ).dropna()
    error = (overlap.public - overlap.crsp).abs()
    if len(error) < 20 or overlap.crsp.abs().gt(0.001).sum() < 8:
        return "insufficient recovery"
    if error.median() > 0.0005 or error.quantile(0.95) > 0.003:
        return "incompatible connection returns"
    return "ok"


def build():
    receipt_path = RAW / "receipts.json"
    receipts = json.loads(receipt_path.read_bytes())
    candidates = cohort()
    directory = pd.read_csv(RAW / "nasdaqtraded.txt", sep="|")
    symbols = directory.loc[
        (directory["Test Issue"] == "N") & (directory.ETF == "N"), "Symbol"
    ]
    by_root = candidate_symbols(candidates, symbols)
    by_id, by_cusip, holding_date = references(candidates)
    choices = {
        r.permno: sorted(set(by_root.get(r.ticker, [])) | set(by_id[r.permno]))
        for r in candidates.itertuples()
    }
    expected = {s for group in choices.values() for s in group}
    if expected - receipts.keys():
        raise ValueError("Collection of symbols is still incomplete")
    cal = xcals.get_calendar("XNYS")
    sessions = cal.sessions_in_range(FIRST, END).tz_localize(None)
    dates = sessions[sessions > ANCHOR]
    boundary = (
        pd.Series(sessions, index=sessions).groupby(sessions.to_period("M")).max()
    )
    ends = boundary.loc["2025-12":].tolist()
    fx = pd.read_parquet(CAT / "fx.parquet").set_index("day").value
    fx.index = pd.to_datetime(fx.index)
    fx = fx.reindex(sessions)
    local = overlap_cache()
    decisions = []
    day_frames = []
    month_frames = []
    events_out = []
    paths = {}
    verified = {}
    official_events = json.loads(
        Path("config/actions-2026-evenements.json").read_bytes()
    )
    for row in candidates.itertuples():
        entry = official_events.get(row.ticker, {})
        event = entry if entry.get("issuer") == row.issuer else {}
        eligible = []
        reasons = []
        for sym in choices[row.permno]:
            status = receipts[sym]["status"]
            if status != "ok":
                reasons.append(status)
                continue
            p = RAW / (sym + ".json.gz")
            paths[sym] = p
            try:
                meta, price, events = read_chart(p, sessions)
                why = inspect_link(
                    row,
                    sym,
                    meta,
                    price,
                    events,
                    local.get(row.permno, pd.Series(dtype=float)),
                    by_cusip.get(row.cusip, set())
                    | ({event["symbol"]} if event.get("type") == "rename" else set()),
                )
            except ValueError as exc:
                why = (
                    str(exc)
                    if str(exc)
                    in (
                        "no sessions issued",
                        "instrument/currency/place",
                        "calendrier",
                    )
                    else "invalid public data"
                )
            except (
                KeyError,
                IndexError,
                TypeError,
                ZeroDivisionError,
            ):
                why = "invalid public data"
            if why == "ok":
                eligible.append(sym)
            else:
                reasons.append(why)
        record = dict(
            permno=row.permno,
            issuer=row.issuer,
            ticker_2025=row.ticker,
            cusip_2025=row.cusip,
            symbol=None,
            status="unmatched",
            detail=" | ".join(sorted(set(reasons))),
            candidates=",".join(choices[row.permno]),
        )
        if event:
            record.update(
                event_date=event["date"],
                event_source=event["source"],
                event_type=event["type"],
                exit_cash_usd=event.get("usd_per_share"),
            )
        if event.get("type") == "cash_exit":
            record.update(
                status="documented exit",
                detail="cash buyback, daily trajectory to complete",
            )
        elif len(eligible) == 1:
            record.update(
                symbol=eligible[0],
                status="close",
                detail="",
                cusip_confirmed=eligible[0] in by_cusip.get(row.cusip, set()),
            )
            verified.setdefault(eligible[0], []).append(row.permno)
        elif len(eligible) > 1:
            record.update(detail="several compatible classes")
        decisions.append(record)
    for record in decisions:
        symbol = record["symbol"]
        if symbol is None:
            continue
        if len(verified[symbol]) != 1:
            record.update(
                symbol=None,
                status="unmatched",
                detail="symbol shared between several PERMNO",
            )
            continue
        meta, price, events = read_chart(paths[symbol], sessions)
        price["chf"] = (1 + price.usd) * (fx / fx.shift(1)) - 1
        added = price.loc[dates].copy()
        active = added.close.notna() & added.adjusted.notna() & added.volume.gt(0)
        # Extreme moves or breaks in dividend adjustment can require a corporate-action review.
        adjustment = price.adjusted / price.close
        jumps = adjustment.pct_change(fill_method=None).abs().loc[dates].gt(0.02)
        declared = {e["day"] for e in events}
        unexplained = any(
            d.date().isoformat() not in declared for d in jumps[jumps].index
        )
        flags = []
        if unexplained:
            flags.append("adjustment without published event")
        if added.usd.gt(1).any() or added.usd.lt(-0.75).any():
            flags.append("extreme daily variation")
        previous = price.close.shift()
        changes = adjustment.pct_change(fill_method=None)
        for event in events:
            day = event["day"]
            if (
                event["kind"] != "dividends"
                or not ANCHOR < day <= END
                or day not in previous.index
            ):
                continue
            cash = event["amount"]
            if pd.isna(previous[day]) or not cash or previous[day] <= cash:
                flags.append("dividend to be controlled")
                break
            expected_change = cash / (previous[day] - cash)
            if abs(changes[day] - expected_change) > max(
                0.0025, 0.10 * expected_change
            ):
                flags.append("dividend and divergent adjustment")
                break
        review = bool(flags)
        status = "complete" if active.all() else "partial"
        if review:
            status = "event to verify"
        record.update(
            status=status,
            detail=", ".join(flags),
            public_name=meta.get("longName") or meta.get("shortName"),
            sessions_priced=int(added.adjusted.notna().sum()),
            sessions_traded=int(active.sum()),
            sessions_chf=int(added.chf.notna().sum()),
            last_priced=str(added.adjusted.last_valid_index())[:10],
        )
        added["permno"] = record["permno"]
        added["symbol"] = symbol
        added["quality"] = status
        added.index.name = "day"
        day_frames.append(added.reset_index())
        levels = price.adjusted.reindex(ends)
        monthly = pd.DataFrame(
            {
                "usd": levels.pct_change(fill_method=None),
                "chf": (levels * fx.reindex(ends)).pct_change(fill_method=None),
            }
        ).iloc[1:]
        monthly.index.name = "day"
        monthly["permno"] = record["permno"]
        monthly["quality"] = status
        month_frames.append(monthly.reset_index())
        for e in events:
            if ANCHOR < e["day"] <= END:
                events_out.append(dict(permno=record["permno"], symbol=symbol, **e))
    aud = pd.DataFrame(decisions)
    daily = pd.concat(day_frames, ignore_index=True)
    months = pd.concat(month_frames, ignore_index=True)
    assert (
        not daily.duplicated(["permno", "day"]).any()
        and not months.duplicated(["permno", "day"]).any()
    )
    assert len(aud) == len(candidates) == aud.permno.nunique()
    summary = dict(
        cohort=len(aud),
        anchor=ANCHOR,
        end=END,
        sessions=len(dates),
        fx_returns_available=int((fx / fx.shift()).loc[dates].notna().sum()),
        status={str(k): int(v) for k, v in aud.status.value_counts().items()},
        bars=int(daily.adjusted.notna().sum()),
        reviewed_symbols=len(expected),
        verified_links=aud.symbol.notna().sum().item(),
        events=len(events_out),
        months_chf=int(months.chf.notna().sum()),
        directory_url=DIRECTORY,
        directory_stamp=(RAW / "nasdaqtraded.txt")
        .read_text()
        .splitlines()[-1]
        .split("|")[0],
    )
    examples = aud[aud.ticker_2025.isin(["AAPL", "MSFT", "NVDA", "BRK", "JPM", "WMT"])][
        ["ticker_2025", "symbol", "status", "sessions_traded", "sessions_chf"]
    ].fillna(0)
    summary["cusip_confirmed"] = int(
        aud.loc[aud.symbol.notna(), "cusip_confirmed"].eq(True).sum()
    )
    summary["sptm_asof"] = holding_date
    for i, row in examples.iterrows():
        series = months[months.permno.eq(aud.loc[i, "permno"])].sort_values("day")
        if len(series) == 10 and series[["usd", "chf"]].notna().all().all():
            examples.loc[i, "total_usd"] = float((1 + series.usd).prod() - 1)
            examples.loc[i, "total_chf"] = float((1 + series.chf).prod() - 1)
    summary["examples"] = json.loads(
        examples.to_json(orient="records", double_precision=10)
    )
    summary["complete_months_chf"] = int(
        months.groupby("permno").chf.count().eq(10).sum()
    )
    summary["unresolved_reasons"] = {
        str(k): int(v) for k, v in aud[aud.symbol.isna()].detail.value_counts().items()
    }
    # One long panel with a single date boundary and an explicit origin on every observation.
    hist_path = CAT / "stock_returns.parquet"
    headers = json.loads((CAT / "manifest.json").read_bytes())
    checked(hist_path, headers["products"][hist_path.name])
    match = json.loads(Path("config/faisabilite-5.json").read_bytes())
    from ..feasibility.inputs import daily_inputs, signature

    sig, _ = signature(match)
    source_daily = Path("data/local/5/cache") / sig / "daily.parquet"
    if not source_daily.is_file():
        daily_inputs(match, sig)
    fund = pd.read_parquet(CAT / "prices.parquet", columns=["id", "day", "return_chf"])
    fund["ticker"] = fund.id.str.rsplit("-", n=1).str[-1]
    factors = (
        fund.pivot(index="day", columns="ticker", values="return_chf")
        .sort_index()
        .loc[:END]
        .tail(504)
    )
    factor_days = set(factors[["SPY", "IEF", "GLD"]].dropna().index)
    old = pd.read_parquet(
        source_daily, filters=[("day", ">=", factors.index[0]), ("day", "<=", ANCHOR)]
    )
    old_counts = old.loc[old.day.isin(factor_days)].groupby("permno").chf.count()
    new_counts = (
        daily.loc[daily.day.isin(pd.to_datetime(sorted(factor_days)))]
        .groupby("permno")
        .chf.count()
    )
    sufficient = (
        old_counts.add(new_counts, fill_value=0)
        .reindex(aud.permno)
        .fillna(0)
        .to_numpy()
    )
    aud["comments_504"] = sufficient.astype(int)
    summary["complete_with_252"] = int(
        (aud.status.eq("complete") & aud.observations_504.ge(252)).sum()
    )
    raw_hashes = {
        s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in sorted(paths.items())
    }
    raw_hashes["directory"] = hashlib.sha256(
        (RAW / "nasdaqtraded.txt").read_bytes()
    ).hexdigest()
    for file in ("SPTM.xlsx", "SEC.json", "receipts.json"):
        raw_hashes[file] = hashlib.sha256((RAW / file).read_bytes()).hexdigest()
    raw_hashes["crsp_daily_cache"] = hashlib.sha256(
        source_daily.read_bytes()
    ).hexdigest()
    snapshot = hashlib.sha256(
        json.dumps(
            [
                raw_hashes,
                choices,
                official_events,
                summary,
                headers["products"][hist_path.name],
                match["sha256_crsp_dsf"],
                hashlib.sha256(
                    b"".join(
                        p.read_bytes()
                        for p in sorted(Path(__file__).parent.glob("*.py"))
                    )
                ).hexdigest(),
            ],
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:16]
    summary["snapshot"] = snapshot
    out = BASE / snapshot
    with TemporaryDirectory(dir=BASE) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, frame in [
            ("inventory", aud),
            ("daily_extension", daily),
            ("monthly_extension", months),
            ("events", pd.DataFrame(events_out)),
        ]:
            frame.to_parquet(stage / (name + ".parquet"), index=False)
        aud.to_csv(stage / "inventory.csv", index=False)
        aud.loc[aud.status.ne("complete")].to_csv(stage / "a_completer.csv", index=False)
        con = duckdb.connect()
        sql = """SELECT permno, cast(day as date) AS day, usd, chf, 'CRSP' AS source, reason AS quality
               FROM read_parquet(?) WHERE day<=CAST(? AS DATE)
               UNION ALL SELECT permno,cast(day as date),usd,chf,'Yahoo Finance',quality FROM read_parquet(?)"""
        con.sql(
            sql,
            params=[str(hist_path), ANCHOR, str(stage / "monthly_extension.parquet")],
        ).write_parquet(str(stage / "monthly_combined.parquet"), compression="zstd")
        daily_sql = """SELECT permno,cast(day as date) AS day,chf,'CRSP' AS source,'historique' AS quality
                     FROM read_parquet(?) WHERE day<=?
                     UNION ALL SELECT permno,cast(day as date),chf,'Yahoo Finance',quality FROM read_parquet(?)"""
        con.sql(
            daily_sql,
            params=[str(source_daily), ANCHOR, str(stage / "daily_extension.parquet")],
        ).write_parquet(str(stage / "daily_combined_chf.parquet"), compression="zstd")
        for name in ("daily_combined_chf", "monthly_combined"):
            path = str(stage / (name + ".parquet"))
            result = con.execute(
                """SELECT count(*)-count(DISTINCT (permno,day)),
                                  count(*) FILTER (WHERE (source='CRSP') != (day <= DATE '2025-12-31'))
                                  FROM read_parquet(?)""",
                [path],
            ).fetchone()
            if result != (0, 0):
                raise ValueError("Duplicate or overlap between sources in " + name)
        con.close()
        (stage / "source_hashes.json").write_text(
            json.dumps(raw_hashes, sort_keys=True)
        )
        (stage / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2)
        )
        hashes = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()
        }
        (stage / "manifest.json").write_text(json.dumps(hashes, sort_keys=True))
        if out.exists():
            for name, digest in json.loads(
                (out / "manifest.json").read_bytes()
            ).items():
                checked(out / name, digest)
        else:
            stage.rename(out)
    REPORT.mkdir(parents=True, exist_ok=True)
    atomic(REPORT / "resultats.json", (out / "summary.json").read_bytes())
    print(out, summary["status"], flush=True)


if __name__ == "__main__":
    build()
