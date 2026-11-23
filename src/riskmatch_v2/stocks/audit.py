"""Audit the raw CIZ extracts and reconcile individual corporate actions."""

import json
from pathlib import Path

import pandas as pd

from ..equity_extension.fetch import CAT
from ..library.sources import checked
from ..universe.data import BR, EQ, US

LOCAL = Path("data/local/9")
REPORT = Path("reports/09-stocks")
MONTH = Path("data/local/4/raw/crsp_msf.csv")
DAILY = Path("data/local/5/raw/crsp_dsf.csv")


def records(frame):
    return json.loads(
        frame.to_json(orient="records", date_format="iso", double_precision=12)
    )


def audit(db):
    sources = json.loads(Path("config/sources-4.json").read_text())
    inputs = json.loads(Path("config/faisabilite-5.json").read_text())
    checked(MONTH, sources[MONTH.name]["sha256"])
    checked(DAILY, inputs["sha256_crsp_dsf"])

    def query(sql):
        return db.sql(sql).df()

    out = {}
    for label, path, day, price, ret, code in [
        ("Daily", DAILY, "DlyCalDt", "DlyPrc", "DlyRet", "Ticker"),
        ("Monthly", MONTH, "MthCalDt", "MthPrc", "MthRet", "Ticker"),
    ]:
        extras = (
            ",count_if(try_cast(MthVol as double) is null) missing_volume, count_if(MthDelFlg!='N') delisting_rows"
            if label == "Monthly"
            else ""
        )
        sql = f"""select year(try_cast({day} as date)) as year, min({day}) first_date,max({day}) last_date,
        count(*) as rows,count(distinct PERMNO) as securities,
        count_if(try_cast({price} as double) is null) missing_price,
        count_if(try_cast({ret} as double) is null) missing_return,
        count_if({code} is null) missing_ticker {extras}
        from read_csv('{path}',all_varchar=true) group by 1 order by 1"""
        out[label] = records(query(sql))
    cols = pd.read_csv(DAILY, nrows=0).columns
    assert "DlyRet" in cols and "DlyVol" not in cols
    # Restrict to fully observed exchange months on a common set of securities.
    monthly = query(f"""with calendar as (select substr(day,1,7) ym,count(*) n from '{CAT}/prices.parquet'
        where ends_with(id,'-SPY') and day between '2025-01-01' and '2025-12-31' group by 1),
        daily as (select permno,strftime(day,'%Y-%m') ym,count(usd) n,product(1+usd order by day)-1 compounded
        from '{EQ}' where year(day)=2025 group by 1,2)
        select m.permno,m.day,m.local_return, compounded, abs(m.local_return-compounded)*10000 error_bp
        from '{CAT}/stock_months.parquet' m join daily d on d.permno=m.permno and d.ym=strftime(m.day,'%Y-%m')
        join calendar c on d.ym=c.ym and d.n=c.n where {US} and m.local_return is not null and m.del_flag='N' order by m.permno,m.day""")
    # Manual independent reconstruction of an ordinary cash ex-dividend return.
    e = query(f"""select dividend,cast(ex_date as varchar) ex_date,cast(payment_date as varchar) pay_date
        from '{CAT}/stock_events.parquet' where permno=14593 and ex_date='2025-02-10' and distribution_type='CD'""").iloc[
        0
    ]
    bars = query(
        f"""select usd,close from '{EQ}' where permno=14593 and day in ('2025-02-07','2025-02-10') order by day"""
    )
    reconstructed = (bars.close.iloc[1] + e.dividend) / bars.close.iloc[0] - 1
    assert abs(reconstructed - bars.usd.iloc[1]) < 1e-5
    exits = query(f"""with terminal as (select permno,max(security_end) final from '{CAT}/identifiers.parquet' group by 1),
      events as (select e.permno,e.ex_date,count(*) events,min(e.distribution_type) kind,min(e.payment_type) currency,
          min(e.dividend) cash,min(e.payment_date) pay,min(e.share_factor) factor
          from '{CAT}/stock_events.parquet' e join terminal t on t.permno=e.permno and e.ex_date between t.final and t.final+interval '7 days'
          group by 1,2 having events=1 and kind='CP' and currency='USD' and factor=-1 and cash>0 and pay is not null)
      select * from events where ex_date between '2017-01-01' and '2025-12-31' order by ex_date,permno""")
    # A terminal file can encode a return with cash already included. Check against
    # formal consideration and the last pre-exit month-end close on a simple acquisition.
    sample = query(f"""select m.permno,m.ticker,cast(m.day as varchar) month_end,
         m.local_return terminal_return,p.price prior_close,m.price last_quote
         from '{CAT}/stock_months.parquet' m join '{CAT}/stock_months.parquet' p
         on m.permno=p.permno and m.previous_day=p.day where m.permno=19567
         and m.day='2021-03-31' and m.return_flag='DE' and m.exit_payment='CASH'""")
    sample["cash"] = 60.0
    sample["completion"] = "2021-04-01"
    sample["source"] = (
        "https://www.merck.com/news/merck-completes-acquisition-of-pandion-therapeutics/"
    )
    assert (
        len(sample) == 1
        and abs((sample.cash / sample.prior_close - 1 - sample.terminal_return).iloc[0])
        < 1e-6
    )
    rename = query(f"""select permno,ticker,issuer,cast(day as varchar) as day from '{CAT}/stock_months.parquet'
         where ticker in ('FB','META') and day in ('2022-05-31','2022-06-30') and issuer like 'META PLATFORMS%' order by day""")
    assert (
        len(rename) == 2
        and rename.permno.nunique() == 1
        and rename.ticker.nunique() == 2
    )
    bridge = json.loads(Path("reports/actions-2026/resultats.json").read_text())
    inv = pd.read_parquet(BR / "inventory.parquet")
    assert len(inv) == sum(bridge["status"].values())
    return (
        {
            "raw": out,
            "fields": {
                label: list(pd.read_csv(path, nrows=0).columns)
                for label, path in [("Daily", DAILY), ("Monthly", MONTH)]
            },
            "agreement": {
                "year": 2025,
                "pairs": len(monthly),
                "securities": monthly.permno.nunique(),
                "median_error_bp": monthly.error_bp.median(),
                "p95_error_bp": monthly.error_bp.quantile(0.95),
                "over_1bp": int((monthly.error_bp > 1).sum()),
            },
            "dividend": {
                "issuer": "Apple",
                "dividend": e.dividend,
                "ex_date": e.ex_date,
                "pay_date": e.pay_date,
                "previous_usd": bars.close.iloc[0],
                "close_usd": bars.close.iloc[1],
                "reconstructed": reconstructed,
                "reported": bars.usd.iloc[1],
            },
            "rename": records(rename),
            "exit": records(sample)[0],
            "documented_cash_events": len(exits),
            "bridge": bridge["status"],
            "directory_timestamp": bridge["directory_stamp"],
            "overlap_tested_links": bridge["verified_links"],
        },
        exits,
        monthly,
    )


def directory_review(cfg, final, ipos):
    """Archive the actual listing-screen snapshot before the decision, including unlinked names."""
    import requests

    venue_rows = []
    for venue, source in cfg["directory"]["files"].items():
        path = LOCAL / "raw" / (venue + ".json")
        if not path.exists():
            resp = requests.get(source["url"], timeout=60)
            resp.raise_for_status()
            tmp = path.with_suffix(".download")
            tmp.write_bytes(resp.content)
            checked(tmp, source["sha256"])
            tmp.replace(path)
        checked(path, source["sha256"])
        data = pd.read_json(path, dtype={"symbol": "string", "ipoyear": "string"})
        venue_rows.append(data.assign(venue=venue))
    listings = pd.concat(venue_rows, ignore_index=True)

    def symbol(series):
        return (
            series.str.strip()
            .str.upper()
            .str.replace(".", "-", regex=False)
            .str.replace("/", "-", regex=False)
        )

    names = symbol(listings.symbol)
    ipo_names = symbol(ipos.proposedTickerSymbol)
    final_names = symbol(final.symbol)
    listings["cohort_symbol_candidate"] = names.isin(final_names)
    listings["ipo_symbol_candidate"] = names.isin(ipo_names)
    listings["screened_symbol_candidate"] = names.isin(final_names[final.pass_research])
    listings["review"] = (
        "Outside verified cohort; history and permanent identity unresolved"
    )
    listings.loc[
        listings.country.ne("United States") & listings.country.notna(), "review"
    ] = "Non-US screener country; flag for issuer review"
    listings.loc[listings.ipo_symbol_candidate, "review"] = (
        "IPO candidate; check identity and pre-listing history"
    )
    listings.loc[listings.cohort_symbol_candidate, "review"] = (
        "Symbol also in cohort; use the independently checked PERMNO bridge"
    )
    return listings, {
        "published_utc": cfg["directory"]["published_utc"],
        "venues": listings.venue.value_counts().to_dict(),
        "securities_in_snapshot": len(listings),
        "matched_final_screen_symbols": int(
            final_names[final.pass_research].isin(names).sum()
        ),
        "outside_cohort_symbols": int((~listings.cohort_symbol_candidate).sum()),
        "us_labelled_outside_cohort": int(
            (
                ~listings.cohort_symbol_candidate & listings.country.eq("United States")
            ).sum()
        ),
        "ipo_symbols_seen": int(ipo_names.isin(names).sum()),
    }
