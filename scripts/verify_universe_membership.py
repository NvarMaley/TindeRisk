"""Verify chapter 3 historical candidate memberships and emit local evidence."""

import csv
import gzip
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

import duckdb
from audit_research_extensions import check, latest
from build_research_windows import BASE, DATA, RAW, save_rows
from build_treasury_identity import build, verified_rows


def equity(db):
    (monthly,) = DATA.glob("new data */data_plus/raw/wrds/crsp_msf.csv")
    delivery = json.loads((BASE / "wrds_delivery.json").read_text())["tables"]["delistings"]
    (delists,) = DATA.glob("telecharger */" + delivery["file"])
    db.execute(
        """create temp table ranked as
        with raw as (select *,try_cast(MthCap as double) cap,try_cast(MthVol as double) vol
        from read_csv(?,all_varchar=true)
        where SecurityType='EQTY' and SecuritySubType='COM' and ShareType='NS' and USIncFlg='Y'
          and IssuerType in ('CORP','ACOR') and PrimaryExch in ('N','A','Q')
          and TradingStatusFlg='A' and ConditionalType='RW'
          and MthCalDt between SecInfoStartDt and SecInfoEndDt
          and MthCalDt between SecurityBegDt and SecurityEndDt),
        unique_caps as (select cast(MthCalDt as date) as day,cast(PERMNO as bigint) id,
          max(cap) cap,min(vol) volume from raw where isfinite(cap) and cap>0
          group by 1,2 having min(cap)=max(cap))
        select *,row_number() over(partition by day order by cap desc,id) as rank
        from unique_caps qualify rank<=1000""",
        [str(monthly)],
    )
    diff = db.execute(
        """select count(*) from ranked full join read_csv_auto(?) r
      on day=ranking_date and id=permno and ranked.rank=r.rank where day is null or ranking_date is null""",
        [str(BASE / "monthly_stock_candidates.csv.gz")],
    ).fetchone()[0]
    if diff:
        raise ValueError(f"Conflicting reconstructed ranks: {diff}")
    db.execute(
        """create temp table events as select distinct try_cast(permno as bigint) id,
        try_cast(delistingdt as date) delisted from read_csv(?,all_varchar=true)
        where try_cast(delistingdt as date) is not null""",
        [str(delists)],
    )
    # Subsequent events are outcome metadata; they never determine the historical ranks.
    rows = db.execute("""with dated as (select *,lead(day) over(order by day) next_review
                         from (select distinct day from ranked)),
        cohort as (select r.*,d.next_review from ranked r join dated d using(day))
        select c.day,c.id,c.rank,c.cap,c.volume,c.next_review,
          min(e.delisted) filter(where e.delisted>c.day and e.delisted<=c.next_review) as subsequent_exit,
          case when exists(select 1 from events x where x.id=c.id and x.delisted=c.day) then 'hold_exit_at_review'
               when c.volume is null or c.volume<=0 then 'hold_missing_positive_volume'
               else 'ranked_candidate' end as decision
        from cohort c left join events e on e.id=c.id
        group by c.day,c.id,c.rank,c.cap,c.volume,c.next_review order by c.day,c.rank""").fetchall()
    counts = Counter(r[0] for r in rows)
    if not counts or set(counts.values()) != {1000}:
        raise ValueError("Unexpected cohort size")
    file = save_rows(
        "stock-membership-evidence",
        [
            "ranking_date",
            "permno",
            "rank",
            "market_cap_source_units",
            "reported_month_volume",
            "next_review",
            "subsequent_exit",
            "decision_after_close",
        ],
        rows,
    )
    return {
        "months": len(counts),
        "rows": len(rows),
        "exits": sum(r[-2] is not None for r in rows),
        "decisions": dict(Counter(r[-1] for r in rows)),
        "first": str(min(counts)),
        "last": str(max(counts)),
        "file": file,
    }


def sovereign():
    master = build(verified_rows(RAW / "public_universe", date.today()), date.today())
    issues = {r["cusip"]: r for r in master["rows"]}
    families = {
        "Bills Maturity Value": "treasury_bill",
        "Notes": "treasury_note",
        "Bonds": "treasury_bond",
        "Inflation-Protected Securities": "tips",
    }
    folder, receipt = latest(RAW / "monthly_treasury_debt", "*/receipt-*.json")
    evidence = {}
    for page in receipt["pages"]:
        with gzip.open(check(folder, page["file"])) as stream:
            for row in json.load(stream)["data"]:
                key = row["security_class2_desc"]
                kind = families.get(row["security_class1_desc"])
                amount = row["outstanding_amt"]
                if (
                    not kind
                    or len(key) != 9
                    or not key.isalnum()
                    or amount in (None, "null", "")
                    or Decimal(amount) <= 0
                ):
                    continue
                day = row["record_date"]
                issue = issues.get(key)
                if not issue:
                    status = "hold_no_auction_identity"
                elif issue["instrument_type"] != kind or issue["maturity"] != row["maturity_date"]:
                    status = "hold_terms_disagree"
                elif (
                    not max(issue["first_observed_issue_date"], issue["first_observed_record_date"])
                    <= day
                    < issue["maturity"]
                ):
                    status = "hold_outside_verified_dates"
                else:
                    status = "confirmed_at_statement_date"
                obs = (day, key, kind, row["maturity_date"], status)
                if (day, key) in evidence and evidence[day, key] != obs:
                    raise ValueError("Conflicting Treasury statement evidence")
                evidence[day, key] = obs
    rows = sorted(evidence.values())
    dates = sorted({r[0] for r in rows})
    file = save_rows(
        "sovereign-statement-membership",
        ["statement_date", "cusip", "class", "reported_maturity", "decision"],
        rows,
    )
    counts = Counter(r[-1] for r in rows)
    return {
        "months": len(dates),
        "last": dates[-1],
        "latest_confirmed": sum(
            r[0] == dates[-1] and r[-1] == "confirmed_at_statement_date" for r in rows
        ),
        "decisions": dict(counts),
        "file": file,
    }


def treasury_funds():
    folder, receipt = latest(RAW / "nport_accession_positions", "*/receipt-*.json")
    evidence = set()
    for quarter in receipt["quarters"]:
        if "file" not in quarter:
            continue
        with gzip.open(check(folder, quarter["file"])) as stream:
            for row in json.load(stream):
                if (
                    row["asset_cat"] == "STIV"
                    and row["issuer_type"] != "UST"
                    and Decimal(row["percentage"] or "0") > 0
                ):
                    evidence.add(row["accession_number"])
    folder, receipt = latest(BASE / "nport_acceptance")
    rows = set()
    with gzip.open(check(folder, receipt["file"]), "rt") as stream:
        for r in csv.DictReader(stream):
            key = r["accession"]
            rows.add(
                (
                    r["ticker"],
                    r["reported"],
                    key,
                    "excluded_non_treasury_holding" if key in evidence else "hold_unverified",
                )
            )
    if {r[0] for r in rows} != {"BIL", "IEF", "SHY", "TIP", "TLT"} or {
        r[2] for r in rows
    } != evidence:
        raise ValueError("Fund holdings review is incomplete")
    file = save_rows(
        "treasury-fund-decisions", ["ticker", "report_date", "accession", "decision"], sorted(rows)
    )
    return {"funds": 5, "excluded_reports": len(rows), "file": file}


def main():
    with duckdb.connect() as db:
        stock = equity(db)
    report = {
        "audited_on": date.today().isoformat(),
        "stocks": stock,
        "treasuries": sovereign(),
        "funds": treasury_funds(),
    }
    with NamedTemporaryFile("w", dir=BASE, delete=False) as temp:
        json.dump(report, temp, indent=2)
    Path(temp.name).replace(BASE / "universe_membership_review.json")
    print(
        {
            k: {a: b for a, b in v.items() if a != "file"}
            for k, v in report.items()
            if isinstance(v, dict)
        }
    )


if __name__ == "__main__":
    main()
