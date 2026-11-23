"""Rebuild all four stock research items from the frozen research archives."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pandas as pd

from ..equity_extension.fetch import CAT
from ..universe.data import BR
from .audit import LOCAL, REPORT, audit, directory_review, records
from .filings import filings
from .universe import analyse, historical, issuer_overlap


def run():
    cfgfile = Path("config/stocks-9.json")
    cfg = json.loads(cfgfile.read_bytes())
    parent = json.loads(Path("config/econometrie.json").read_bytes())
    base = Path("data/local/univers") / cfg["universe_snapshot"]
    db = duckdb.connect()
    db.execute("set threads=4")
    LOCAL.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    audit_result, exits, agreement = audit(db)
    print("Extract and events audited", flush=True)
    reg, book, picks, stats, sectors = analyse(db, base, cfg, parent)
    print("Dated research screens completed", flush=True)
    annual, sector_history, history_examples = historical(db, reg, cfg)
    finance, versions, latest = filings(db, cfg)
    final = reg[reg.day.eq(cfg["decision"])]
    finance["in_final_inventory"] = int(final.permno.isin(latest.permno).sum())
    finance["in_final_screen"] = int(
        final.loc[final.pass_research, "permno"].isin(latest.permno).sum()
    )
    # Keep non-matches, with an explicit reason and no default fundamental value.
    profile = final[["permno", "symbol", "pass_research"]].merge(
        latest, on="permno", how="left", validate="one_to_one"
    )
    profile["fundamental_status"] = profile.adsh.notna().map(
        {True: "Dated balance sheet", False: "No verified balance sheet"}
    )
    ipo = pd.read_parquet(base / "ipos.parquet").copy()
    ipo["review"] = (
        "New-deal record; prior identity or longer eligible trading history unverified"
    )
    listings, directory = directory_review(cfg, final, ipo)
    ipodup = ipo.dealID.duplicated().sum()
    freeze = json.loads(Path("reports/04-catalogue/resultats.json").read_bytes())
    comparison = book.pivot(index="day", columns="book", values="net_return")
    paired = comparison.dropna()
    spread = paired["SPY plus stocks"] - paired["SPY only"]
    reason = (
        reg.groupby(["day", "screen_reason"]).size().rename("securities").reset_index()
    )
    terminal = db.sql(f"""select m.permno,m.day,m.del_flag,m.exit_payment,m.return_flag,m.local_return,
        case when m.return_flag='DE' and m.local_return is not null and m.exit_payment='CASH'
             then 'Cash included in terminal return' when m.exit_payment in ('STK','CST')
             then 'Successor or mixed consideration requires tracing' else 'Settlement requires evidence' end as outcome
        from '{CAT}/stock_months.parquet' m where m.del_flag!='N' and m.country_flag='Y' and m.security_type='EQTY'
        and m.subtype='COM' and m.share_type='NS' and m.exchange in ('N','Q','A')""").df()
    extraction = db.sql(f"""select cast(day as varchar) as day,
          case when country_flag is distinct from 'Y' then 'Non-US or unknown incorporation'
          when security_type is distinct from 'EQTY' or subtype is distinct from 'COM' or share_type is distinct from 'NS' then 'Other share or security type'
          when exchange is null or exchange not in ('N','Q','A') then 'Other or missing exchange'
          else 'US common share in scope' end reason,count(*) securities
          from '{CAT}/stock_months.parquet' where month(day)=10 group by 1,2 order by 1,2""").df()
    summary = {
        "extraction_scope": records(extraction),
        "date": cfg["decision"],
        "audit": audit_result,
        "screen": records(stats),
        "reasons": records(reason),
        "portfolios": records(book),
        "current_stock_selection": records(
            picks[
                (picks.day == cfg["decision"]) & picks.id.str.startswith("PERMNO")
            ].merge(final[["id", "symbol", "participation"]], on="id")
        ),
        "paired": len(paired),
        "positive_spreads": int((spread > 0).sum()),
        "mean_paired_spread": spread.mean(),
        "directory": directory,
        "overlap": freeze["overlap"],
        "mixed_book_overlap": issuer_overlap(picks, final, cfg),
        "ipo_records": len(ipo),
        "duplicate_ipo_deal_ids": int(ipodup),
        "fundamentals": finance,
        "historical_october": records(annual),
        "historical_sectors": records(sector_history),
        "dated_sector_reasons": records(sectors),
        "historical_examples": history_examples,
        "live_allowed": int(reg.live_order_allowed.sum()),
        "current_sector_date": "2025-12-31",
        "terminal_status": terminal.outcome.value_counts().to_dict(),
        "current_reasons": final.screen_reason.value_counts().to_dict(),
    }
    tracked = [
        cfgfile,
        *sorted(Path(__file__).parent.glob("*.py")),
        base / "manifest.json",
        CAT / "manifest.json",
        BR / "manifest.json",
        Path("config/sources-4.json"),
        Path("config/faisabilite-5.json"),
        Path("config/econometrie.json"),
    ]
    hashes = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in tracked}
    stamp = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    summary["archive"] = stamp
    dest = LOCAL / stamp
    if not dest.exists():
        with TemporaryDirectory(dir=LOCAL) as temp:
            stage = Path(temp) / "tables"
            stage.mkdir()
            for name, frame in {
                "research_screen": reg,
                "portfolios": book,
                "positions": picks,
                "dated_cash_events": exits,
                "terminal_months": terminal,
                "return_agreement": agreement,
                "filing_versions": versions,
                "current_fundamentals": profile,
                "listing_register": listings,
                "ipo_review": ipo,
                "sector_history": sector_history,
                "sector_reasons": sectors,
            }.items():
                frame.to_parquet(stage / (name + ".parquet"), index=False)
            (stage / "inputs.json").write_text(json.dumps(hashes, indent=2))
            stage.rename(dest)
    (REPORT / "results.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    print("Archive", dest, flush=True)
    db.close()


if __name__ == "__main__":
    run()
