"""Build local research windows for the frozen universe. Outputs contain licensed identifiers."""

import csv
import gzip
import io
import itertools
import json
import tempfile
from bisect import bisect_right
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
from audit_research_extensions import check, latest
from fetch_market_sessions import DEST as SESSIONS
from fetch_market_sessions import calendar, session
from fetch_public_universe_data import ROOT, immutable_save

DATA = ROOT / "data"
RAW = DATA / "raw"
BASE = DATA / "processed/universe"
OUT = BASE / "research_windows"


def save_rows(name, header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return immutable_save(OUT, name, gzip.compress(buffer.getvalue().encode(), mtime=0), "csv.gz")


def stock_months(db, monthly):
    # Keep every member, including a missing next-month observation or a conflict.
    query = """with ranks as (select * from read_csv_auto(?)),
      dates as (select distinct ranking_date from ranks),
      periods as (select ranking_date,lead(ranking_date) over(order by ranking_date) as end_date from dates),
      source as (select PERMNO,MthCalDt,try_cast(MthRet as double) as r from read_csv(?,all_varchar=true)),
      joined as (select a.ranking_date,p.end_date,a.permno,a.rank,count(s.PERMNO) as observations,
                    min(r) as low,max(r) as high,count(r) as valid
                 from ranks a join periods p using(ranking_date)
                 left join source s on a.permno=try_cast(s.PERMNO as bigint) and p.end_date=try_cast(s.MthCalDt as date)
                 where p.end_date is not null group by all)
      select ranking_date,end_date,permno,rank,
        case when observations=valid and low=high and isfinite(low) and low>=-1 then low end as observed_return
        from joined order by ranking_date,rank"""
    result = db.execute(query, [str(BASE / "monthly_stock_candidates.csv.gz"), str(monthly)])
    rows = result.fetchall()
    missing = Counter(r[0] for r in rows if r[-1] is None)
    covered = {r[0] for r in rows} - missing.keys()
    dataset = save_rows("stock-next-month", [c[0] for c in result.description], rows)
    return {
        "rows": len(rows),
        "missing_returns": sum(missing.values()),
        "complete_months": len(covered),
        "incomplete_months": len(missing),
        "file": dataset,
    }


def stock_exceptions(db):
    folder, receipt = latest(RAW / "public_market_history", "*/receipt-*.json")
    matches = check(BASE / "market_matches", receipt["local_match_file"])
    with gzip.open(matches, "rt") as f:
        cohort = [r for r in csv.DictReader(f) if int(r["sessions"]) < receipt["expected_days"]]
    symbols = [r["snapshot_ticker"] for r in cohort]
    observations = db.execute(
        """select act_symbol,date from read_parquet(?)
      where close>0 and volume>=0 and act_symbol in (select unnest(?))""",
        [str(check(folder, receipt["file"])), symbols],
    ).fetchall()
    dates = defaultdict(set)
    for symbol, day in observations:
        dates[symbol].add(str(day))
    days = set(calendar())
    if len(days) != receipt["expected_days"]:
        raise ValueError("Calendar and market snapshot disagree")
    ref_folder, ref = latest(BASE / "market_matches", "identity-*.json")
    leads = defaultdict(set)
    _, public = latest(RAW / "delisting_reference")
    for entry, source in [
        (ref["lead_file"], "SEC issuer filing"),
        (public["local_leads_file"], "public listing record"),
    ]:
        with gzip.open(check(ref_folder, entry), "rt") as f:
            for line in csv.DictReader(f):
                leads[line["local_permno"]].add(source)
    rows = []
    for r in cohort:
        usable = dates[r["snapshot_ticker"]] if int(r["sessions"]) else set()
        gaps = sorted(days - usable)
        rows.append(
            (
                r["local_permno"],
                r["snapshot_ticker"],
                int(r["sessions"]),
                min(gaps, default=None),
                "|".join(gaps),
                "|".join(sorted(leads[r["local_permno"]])),
                "hold_pending_security_identity_or_terminal_proceeds",
            )
        )
    return save_rows(
        "stock-exceptions",
        [
            "permno",
            "snapshot_ticker",
            "matched_sessions",
            "first_gap",
            "missing_sessions",
            "leads",
            "status",
        ],
        rows,
    )


def coupon_schedule(issues):
    schedules = {}
    for page in sorted((RAW / "public_universe").glob("*/auctions_query-page-*.json")):
        for r in json.loads(page.read_text())["data"]:
            key = r["cusip"]
            if key not in issues or issues[key]["instrument_type"] not in (
                "treasury_note",
                "treasury_bond",
                "tips",
            ):
                continue
            if (
                r.get("reopening"),
                r.get("callable"),
                r.get("first_int_period"),
                r.get("int_payment_frequency"),
            ) != ("No", "No", "Normal", "Semi-Annual"):
                continue
            first = date.fromisoformat(r["first_int_payment_date"])
            maturity = date.fromisoformat(issues[key]["maturity"])
            if maturity.isoformat() != r["maturity_date"] or r["dated_date"] > first.isoformat():
                continue
            if r.get("int_rate") in (None, "", "null") or issues[key]["coupon_rate_decimal"] in (
                None,
                "",
                "null",
            ):
                continue
            coupon = Decimal(r["int_rate"]) / 2  # dollars per 100 nominal per regular half year
            if coupon <= 0 or coupon / 50 != Decimal(issues[key]["coupon_rate_decimal"]):
                continue
            dates = []
            year, month = first.year, first.month
            while (year, month) <= (maturity.year, maturity.month):
                length = monthrange(year, month)[1]
                day = date(
                    year,
                    month,
                    length
                    if maturity.day == monthrange(maturity.year, maturity.month)[1]
                    else min(maturity.day, length),
                )
                dates.append(day)
                year, month = year + (month + 5) // 12, (month + 5) % 12 + 1
            if not dates or dates[0] != first or dates[-1] != maturity:
                continue
            rows = [(key, d, coupon, 100 if d == maturity else 0) for d in dates]
            if key in schedules and schedules[key] != rows:
                raise ValueError("Conflicting original terms")
            schedules[key] = rows
    return schedules


def treasury_windows():
    issues = {
        r["cusip"]: r for r in json.loads((BASE / "treasury_identity.json").read_text())["rows"]
    }
    calendar = []
    observations = defaultdict(dict)
    for folder in sorted((RAW / "fedinvest").iterdir()):
        _, receipt = latest(folder)
        if not receipt:
            continue
        day = receipt["date"]
        calendar.append(day)
        with check(folder, receipt["file"]).open() as f:
            for r in csv.DictReader(f):
                issue = issues.get(r["CUSIP"])
                if not issue or not issue["first_observed_issue_date"] <= day < issue["maturity"]:
                    continue
                value = float(r["END OF DAY"] or 0)
                if value > 0 and r["date"] == day:
                    dates = observations[r["CUSIP"]]
                    if day in dates and dates[day] != value:
                        raise ValueError("Conflicting issue valuation")
                    dates[day] = value
    rows, bill_rows = [], []
    for key, issue in issues.items():
        marks = observations[key]
        expected = [
            d for d in calendar if issue["first_observed_issue_date"] <= d < issue["maturity"]
        ]
        missing = [d for d in expected if d not in marks]
        rows.append(
            (
                key,
                issue["instrument_type"],
                min(marks, default=None),
                max(marks, default=None),
                len(marks),
                len(expected),
                len(missing),
                issue["maturity"],
            )
        )
        if issue["instrument_type"] == "treasury_bill":
            for a, b in itertools.pairwise(expected):
                if a in marks and b in marks:
                    bill_rows.append((key, a, b, marks[b] / marks[a] - 1))
    schedules = coupon_schedule(issues)
    coupons = {k: v for k, v in schedules.items() if issues[k]["instrument_type"] != "tips"}
    accrued = []
    for key, terms in coupons.items():
        dates = [r[1] for r in terms]
        for mark in sorted(observations[key]):
            day = date.fromisoformat(mark)
            index = bisect_right(dates, day)
            if 0 < index < len(dates):
                a, b = dates[index - 1 : index + 1]
                interest = terms[index][2] * Decimal((day - a).days) / Decimal((b - a).days)
                accrued.append((key, day, interest))
    tips = []
    folder, ratios = latest(RAW / "tips_ratios", "*/receipt-*.json")
    for issue in ratios["issues"]:
        key = issue["cusip"]
        if key not in schedules or issues[key]["instrument_type"] != "tips" or "file" not in issue:
            continue
        with gzip.open(check(folder, issue["file"]), "rt") as f:
            daily = {
                r["indexDate"][:10]: Decimal(r["indexRatio"])
                for r in json.load(f)
                if r["cusip"] == key and r["indexType"] == "CPI" and r.get("indexRatio")
            }
        for _, day, real_coupon, principal in schedules[key]:
            ratio = daily.get(day.isoformat())
            if ratio is not None and ratio > 0:
                tips.append(
                    (key, day, ratio, real_coupon * ratio, principal * max(Decimal(1), ratio))
                )

    return {
        "nominal_schedules": len(coupons),
        "accrued_marks": len(accrued),
        "accrued_file": save_rows(
            "nominal-accrual", ["cusip", "valuation_date", "contractual_accrued_per_100"], accrued
        ),
        "tips_issues": len({r[0] for r in tips}),
        "tips_payments": len(tips),
        "tips_file": save_rows(
            "tips-contractual-payments",
            [
                "cusip",
                "contractual_date",
                "published_ratio",
                "indexed_coupon_per_100",
                "redemption_per_100",
            ],
            tips,
        ),
        "scheduled_payments": sum(map(len, coupons.values())),
        "nominal_file": save_rows(
            "nominal-contractual-payments",
            ["cusip", "contractual_date", "coupon_per_100", "redemption_per_100"],
            (r for schedule in coupons.values() for r in schedule),
        ),
        "issues": len(rows),
        "issues_with_marks": sum(bool(r[4]) for r in rows),
        "bill_intervals": len(bill_rows),
        "bill_count": len({r[0] for r in bill_rows}),
        "issue_file": save_rows(
            "treasury-coverage",
            [
                "cusip",
                "type",
                "first_mark",
                "last_mark",
                "observed",
                "expected_on_sampled_dates",
                "missing",
                "maturity",
            ],
            rows,
        ),
        "bill_file": save_rows(
            "bill-mark-returns",
            ["cusip", "start", "end", "government_mark_return_before_maturity"],
            bill_rows,
        ),
    }


def price_bridge(db, monthly, daily):
    products = json.loads((ROOT / "configs/universe_catalog.json").read_text())["instruments"]
    start = "2025-12-31"
    folder, receipt = latest(RAW / "public_market_history", "*/receipt-*.json")
    history = check(folder, receipt["file"])
    anchor = session(start)
    with gzip.open(check(SESSIONS, anchor["file"]), "rt") as f:
        anchor_prices = {r[0]: float(r[4]) for r in json.load(f) if r[4] is not None}
    action_folder, actions = latest(RAW / "public_actions", "*/receipt-*.json")
    events = defaultdict(list)
    dated_events = defaultdict(list)
    cash = defaultdict(list)
    splits = defaultdict(list)
    for kind, meta in actions["tables"].items():
        with gzip.open(check(action_folder, meta["file"]), "rt") as f:
            for row in csv.DictReader(f):
                if start < row["ex_date"] <= receipt["last"]:
                    key = row["act_symbol"], row["ex_date"]
                    dated_events[key].append(kind)
                    if kind == "dividend":
                        cash[key].append(Decimal(row["amount"]))
                    elif kind == "split":
                        splits[key].append((Decimal(row["to_factor"]), Decimal(row["for_factor"])))
                if start < row["ex_date"] <= receipt["first"]:
                    events[row["act_symbol"]].append(kind)
    query = """with ids as (select distinct Ticker,PERMNO from read_csv(?,all_varchar=true)
                where MthCalDt=? and Ticker in (select unnest(?))),
            prices as (select PERMNO,min(try_cast(DlyPrc as double)) lo,max(try_cast(DlyPrc as double)) hi
                from read_csv(?,all_varchar=true) where DlyCalDt=? group by PERMNO),
            first as (select act_symbol,close from read_parquet(?) where date=cast(? as date))
            select ticker,count(distinct i.permno),min(lo),max(hi),min(close)
            from ids i left join prices p using(permno) left join first f on i.ticker=f.act_symbol group by ticker"""
    ids = [r["ticker"] for r in products]
    results = db.execute(
        query, [str(monthly), start, ids, str(daily), start, str(history), receipt["first"]]
    ).fetchall()
    lookup = {r[0]: r[1:] for r in results}
    rows = []
    for symbol in ids:
        n, lo, hi, new = lookup.get(symbol, (0, None, None, None))
        old = anchor_prices.get(symbol)
        # Half a cent accommodates cent rounding only. This checks a price seam, not total return.
        ok = bool(
            n == 1
            and lo == hi
            and lo
            and lo > 0
            and old
            and new
            and new > 0
            and abs(old - lo) <= 0.005001
            and not events[symbol]
        )
        rows.append(
            (
                symbol,
                lo,
                old,
                new,
                ",".join(events[symbol]),
                "matched" if ok else "hold",
                new / old - 1 if ok else None,
            )
        )
    series = db.execute(
        """select act_symbol,date,close,volume from read_parquet(?)
        where act_symbol in (select unnest(?)) order by act_symbol,date""",
        [str(history), ids],
    ).fetchall()
    index = {day: i for i, day in enumerate(calendar())}
    previous = {r[0]: (-1, r[2]) for r in rows if r[-2] == "matched"}
    issuer_folder, issuer_receipt = latest(RAW / "issuer_performance")
    confirmed = {}
    issuer_funds = set()
    for fund in issuer_receipt["funds"]:
        issuer_funds.add(fund["ticker"])
        with gzip.open(check(issuer_folder, fund["file"]), "rt") as f:
            dist = json.load(f)["distributions"]
        for ex, amount in zip(dist["exDate"], dist["totalDistribution"], strict=True):
            ex = str(ex)
            confirmed[fund["ticker"], f"{ex[:4]}-{ex[4:6]}-{ex[6:]}"] = Decimal(str(amount))
    action_horizon = min(m["last"] for m in actions["tables"].values())
    panel = []
    for symbol, day, close, volume in series:
        day = str(day)
        i = index[day]
        prior = previous.get(symbol)
        valid = close is not None and close > 0 and volume is not None and volume > 0
        flags = dated_events[symbol, day]
        price_return = close / prior[1] - 1 if valid and prior and prior[0] == i - 1 else None
        key = symbol, day
        gross = None
        status = "single_source_event_history"
        amounts = cash.get(key, [])
        split = splits.get(key, [])
        amount = sum(amounts, Decimal(0))
        factor = 1
        issuer_amount = confirmed.get(key, Decimal(0))
        # The issuer restates the March distribution per post-split share.
        if key == ("IWF", "2026-03-17") and splits.get(("IWF", "2026-04-29")) == [
            (Decimal(4), Decimal(1))
        ]:
            issuer_amount *= 4
        if day > action_horizon or price_return is None:
            status = "outside_return_window"
        elif len(amounts) > 1 or len(split) > 1 or (split and amounts) or amount < 0:
            status = "ambiguous_event"
        elif split and (key != ("IWF", "2026-04-29") or split != [(Decimal(4), Decimal(1))]):
            status = "unverified_split"
        elif symbol in issuer_funds and abs(issuer_amount - amount) > Decimal("0.00001"):
            status = "distribution_disagreement"
        else:
            if split:
                factor = 4  # OCC Information Memo 58763, 2026-04-29
            if symbol in issuer_funds:
                status = "issuer_distribution_crosscheck"
            gross = (factor * close + float(amount)) / prior[1] - 1
        panel.append(
            (
                symbol,
                day,
                close,
                volume,
                price_return,
                "|".join(sorted(flags)),
                amount,
                factor,
                gross,
                status,
            )
        )
        if valid:
            previous[symbol] = (i, close)
    bars_file = save_rows(
        "listed-market-observations",
        [
            "ticker",
            "date",
            "close",
            "volume",
            "unadjusted_price_return",
            "reported_actions",
            "reported_cash_per_share",
            "applied_split_factor",
            "research_gross_return",
            "return_status",
        ],
        panel,
    )
    return {
        "matched": sum(r[-2] == "matched" for r in rows),
        "total": len(rows),
        "observed_product_days": len(panel),
        "research_returns": sum(r[-2] is not None for r in panel),
        "return_status": dict(Counter(r[-1] for r in panel)),
        "action_product_days": sum(bool(r[5]) for r in panel),
        "bars_file": bars_file,
        "anchor": anchor,
        "file": save_rows(
            "price-bridge",
            [
                "ticker",
                "crsp_dec31",
                "public_dec31",
                "public_jan02",
                "reported_events",
                "status",
                "price_return",
            ],
            rows,
        ),
    }


def main():
    (folder,) = [p for p in DATA.iterdir() if p.name.strip() == "new data"]
    wrds = folder / "data_plus/raw/wrds"
    with duckdb.connect() as db:
        stocks = stock_months(db, wrds / "crsp_msf.csv")
        stocks["exceptions_2026"] = stock_exceptions(db)
        treasuries = treasury_windows()
        bridge = price_bridge(db, wrds / "crsp_msf.csv", wrds / "crsp_dsf.csv")
    summary = {
        "as_of": date.today().isoformat(),
        "stocks": stocks,
        "treasuries": treasuries,
        "bridge": bridge,
    }
    receipt = immutable_save(OUT, "receipt", json.dumps(summary, indent=2).encode(), "json")
    display = {
        "audited_on": summary["as_of"],
        "bridge": bridge["matched"],
        "products": bridge["total"],
        "stock_rows": stocks["rows"],
        "stock_gaps": stocks["missing_returns"],
        "issues_with_marks": treasuries["issues_with_marks"],
        "schedules": treasuries["nominal_schedules"],
        "receipt": receipt,
    }
    with tempfile.NamedTemporaryFile(mode="w", dir=BASE, delete=False) as temp:
        json.dump(display, temp)
    Path(temp.name).replace(BASE / "research_window_summary.json")
    print(
        {
            k: {a: b for a, b in v.items() if isinstance(b, int)}
            for k, v in summary.items()
            if isinstance(v, dict)
        }
    )


if __name__ == "__main__":
    main()
