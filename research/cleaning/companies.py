"""Reconstruct dated security and sector links; keep publication-unknown inputs descriptive."""

import duckdb
import pandas as pd


def company_panels(data, out):
    db = duckdb.connect()
    wrds = data / "additional_data/raw/wrds"
    db.execute("set threads=1")
    db.read_csv(str(wrds / "crsp_msf.csv"), all_varchar=True).create_view("msf")
    db.read_csv(str(wrds / "ccm_lnkhist.csv"), all_varchar=True).create_view("ccm")
    db.read_parquet(
        str(data / "additional_data/clean/monthly_panel.parquet")
    ).create_view("legacy")
    db.execute("""
        create temp table months as
        with variants as (
          select distinct permno::int permno, MthCalDt::date AS day, try_cast(MthRet as double) ret,
            try_cast(MthCap as double) cap_thousands, MthDelFlg del_flag, try_cast(SecurityEndDt as date) security_end,
            try_cast(SecInfoStartDt as date) info_start, try_cast(SecInfoEndDt as date) info_end,
            (PrimaryExch in ('N','A','Q') and SecurityType='EQTY' and SecuritySubType='COM'
             and ShareType='NS' and USIncFlg='Y' and IssuerType='CORP') common_us
          from msf
        ), ranked as (
          select *, dense_rank() over(partition by permno,day order by
            (day between info_start and coalesce(info_end,date '9999-12-31')) desc nulls last,
            info_start desc nulls last) preference from variants)
        select permno,day, count(*) versions,
          case when count(*)=1 then max(ret) end ret,
          case when count(*)=1 then max(cap_thousands) end cap_thousands,
          case when count(*)=1 then max(del_flag) end del_flag,
          case when count(*)=1 then max(security_end) end security_end,
          count(*)=1 and bool_and(common_us and day between info_start and coalesce(info_end,date '9999-12-31')) common_us
        from ranked where preference=1 group by permno,day
    """)
    db.execute("""
        create temp table links as
        select LPERMNO::int permno, gvkey, try_cast(LINKDT as date) starts,
          case when LINKENDDT='E' then date '9999-12-31' else try_cast(LINKENDDT as date) end AS ends,
          (case LINKPRIM when 'P' then 0 else 2 end + case LINKTYPE when 'LC' then 0 else 1 end) priority
        from ccm where LINKTYPE in ('LC','LU') and LINKPRIM in ('P','C') and LPERMNO is not null;
    """)

    # The same priority and tie handling applies to both security-months and tagged company-days.
    def link_ids(source, target):
        db.execute(f"""
            create temp table {target} as
            with candidates as (
               select d.permno,d.day,l.gvkey,l.priority,
                  min(priority) over(partition by d.permno,d.day) best
               from {source} d join links l on d.permno=l.permno and d.day between l.starts and l.ends
            )
            select permno,day,count(distinct gvkey) candidates,
                   count(distinct gvkey) filter(where priority=best) best_count,
                   case when count(distinct gvkey) filter(where priority=best)=1
                        then min(gvkey) filter(where priority=best) end gvkey
            from candidates group by permno,day""")

    link_ids("months", "monthly_ids")
    db.execute("""
        create temp view universe as
        select m.permno,m.day,m.ret,m.cap_thousands,m.common_us,m.versions,
               m.del_flag, coalesce(m.common_us and m.del_flag='N' and m.cap_thousands>0,false) market_candidate,
               l.gvkey,coalesce(l.best_count,0) best_link_count,
               coalesce(l.candidates,0) link_candidates
        from months m left join monthly_ids l using(permno,day)
    """)

    duplicates = db.sql("""
        select count(*) from (select permno,date_trunc('month',day) from months
                              group by all having count(*)>1)""").fetchone()[0]
    if duplicates:
        raise ValueError(
            "Unresolved multiple records for a security in one calendar month"
        )

    def table(query, name):
        path = str(out / name)
        db.sql(query).write_parquet(path, compression="zstd")

    table("select * from universe order by permno,day", "security_universe.parquet")
    counts = db.sql("""
        select year(day) AS year, common_us, case when best_link_count=0 then 'unmatched'
          when best_link_count=1 then 'unique' else 'ambiguous' end link_status,
          count(*) security_months, count(ret) AS observed_returns, avg(ret) mean_ret, median(cap_thousands) median_cap_usd_thousands
        from universe group by all order by all""").df()
    counts.to_csv(out / "company_coverage.csv", index=False)
    # CIZ codes are retained unchanged. Missing observed monthly return and uncertain exit proceeds
    # are separate issues. No additional delisting cash is compounded onto a CIZ total return.
    exits = db.sql("""
        select m.permno,m.day,m.ret,m.del_flag,
          date_trunc('month',m.security_end)=date_trunc('month',m.day) end_month
        from months m
        where m.del_flag <> 'N' or (date_trunc('month',m.security_end)=date_trunc('month',m.day)
          and m.day < (select max(day) from months)) order by day,permno""").df()
    exits["missing_return"] = exits.ret.isna()
    # Treat an ending month without a delist flag, or a missing monthly return, as uncertain.
    uncertain = exits.missing_return | exits.del_flag.fillna("N").isin(["N", "M", "P"])
    exits["uncertain_exit_sensitivity"] = uncertain
    for label, shock in [("minus30", -0.30), ("total_loss", -1.0)]:
        exits[label] = exits.ret.where(
            ~uncertain, (1 + exits.ret.fillna(0)) * (1 + shock) - 1
        )
    exits.to_parquet(out / "terminal_returns.parquet", index=False)
    filings = (
        db.sql("""
        select count(*) imported_months,count(datadate) with_accounts,
          count(*) filter(where available_from>trade_date) after_session,
          count(*) filter(where available_from=trade_date) same_day,
          count(*) filter(where investable and available_from>trade_date) investable_after_session
        from legacy""")
        .df()
        .iloc[0]
        .astype(int)
        .to_dict()
    )
    # No release date or filing vintage in the source header; a lag assumption cannot populate a verified field.
    fields = pd.read_csv(wrds / "comp_funda.csv", nrows=0).columns
    if any(k.lower() in ("rdq", "filing_date", "pdate", "fdate") for k in fields):
        raise ValueError("Filing schema changed; review the v1 publication rule")
    source = pd.read_parquet(
        data / "processed/ln7_company_sector_days.parquet", columns=["ticker", "date"]
    )
    if source.duplicated(["ticker", "date"]).any():
        raise ValueError("Duplicate firm-day")
    db.register("tags", source)
    db.read_csv(str(wrds / "crsp_dsf.csv"), all_varchar=True).create_view("dsf")
    db.execute("""
        create temp table daily_subset as select ticker,permno,DlyCalDt::date as day,
           try_cast(DlyRet as double) as daily_return from dsf
        where ticker in (select distinct ticker from tags) or
              (PERMNO='11300' and DlyCalDt between '1998-01-01' and '1998-01-31')""")
    # A single audited CIZ terminal month can also be rebuilt from the raw daily total returns.
    daily_example = db.sql("""
        select day as session,daily_return from daily_subset
        where PERMNO='11300' and day between '1998-01-01' and '1998-01-31'
        order by session""").df()
    official = exits.loc[
        exits.permno.eq(11300) & exits.day.eq("1998-01-30"), "ret"
    ].item()
    if (
        daily_example.empty
        or daily_example.session.duplicated().any()
        or daily_example.daily_return.isna().any()
    ):
        raise ValueError("Incomplete daily delisting example")
    compounded = float((1 + daily_example.daily_return).prod() - 1)
    if abs(compounded - official) > 1e-5:
        raise ValueError(
            "Daily and monthly terminal returns fail the rounding tolerance"
        )
    terminal_example = {
        "permno": 11300,
        "month": "1998-01",
        "daily_rows": len(daily_example),
        "compounded": compounded,
        "monthly": float(official),
        "difference": compounded - float(official),
    }
    db.execute("""
       create temp table daily_ids as
       select t.ticker,t.date::date AS day,count(distinct d.permno) n_ids,
              case when count(distinct d.permno)=1 then min(d.permno)::int end permno
       from tags t left join daily_subset d
       on t.ticker=d.ticker and t.date=d.day group by t.ticker,t.date""")
    db.execute(
        "create temp view firm_keys as select distinct day,permno from daily_ids where permno is not null"
    )
    link_ids("firm_keys", "firm_links")
    gics = pd.read_csv(data / "raw/GICS.zip", dtype={"gvkey": str, "gsector": str})
    db.register("gics", gics)
    tagged_returns = pd.read_csv(
        next(data.glob("Data for laboratories*/*.csv")),
        usecols=["date", "ticker", "daily_return"],
    )
    tagged_returns["day"] = pd.to_datetime(
        tagged_returns.date, utc=True
    ).dt.tz_localize(None)
    if tagged_returns.duplicated(["ticker", "day"]).any():
        raise ValueError("Duplicate course return")
    db.register("tagged_returns", tagged_returns)
    sectors = db.sql("""
       with matches as (
         select t.ticker,t.day,t.permno,t.n_ids,l.gvkey,l.best_count,count(distinct g.gsector) sectors,
            case when count(distinct g.gsector)=1 then min(g.gsector) end effective_sector
         from daily_ids t left join firm_links l using(permno,day) left join gics g
           on l.gvkey=g.gvkey and t.day>=cast(g.indfrom as date)
           and (g.indthru is null or t.day<=cast(g.indthru as date)) and g.indtype='GICS' group by all
       )
       select m.*,case when n_ids=0 then 'missing PERMNO' when n_ids>1 then 'ambiguous PERMNO'
          when best_count is null then 'missing CCM' when best_count>1 then 'ambiguous CCM'
          when sectors=0 then 'missing sector' when sectors>1 then 'ambiguous sector'
          else 'effective only' end status, r.daily_return, u.cap_thousands prior_month_cap,
          cast(null as varchar) published_sector
       from matches m left join tagged_returns r using(ticker,day)
       left join universe u on m.permno=u.permno and date_trunc('month',u.day)=date_trunc('month',m.day)-interval '1 month'
       order by ticker,day""").df()
    if len(sectors) != len(source) or sectors.duplicated(["ticker", "day"]).any():
        raise ValueError("Sector join multiplied firm-days")
    sectors.to_parquet(out / "sector_days.parquet", index=False)
    sectors["year"] = sectors.day.dt.year
    sectors.groupby(["year", "status", "effective_sector"], dropna=False).agg(
        firm_days=("day", "size"),
        verified_sector=("published_sector", "count"),
        returns=("daily_return", "count"),
        mean_return=("daily_return", "mean"),
        observed_prior_caps=("prior_month_cap", "count"),
        median_prior_cap_thousands=("prior_month_cap", "median"),
    ).reset_index().to_csv(out / "sector_coverage.csv", index=False)
    by_month = db.sql("""select date_trunc('month',a.day)::date AS month, count(*) security_months,
        count(*) filter(where a.market_candidate and a.best_link_count=1) linked_common,
        count(b.ret) filter(where a.market_candidate and a.best_link_count=1) next_returns
        from universe a left join universe b on a.permno=b.permno
          and date_trunc('month',b.day)=date_trunc('month',a.day)+interval '1 month'
        group by month order by month""").df()
    integrity = (
        db.sql("""select count(*) security_months,count(*) filter(where versions>1) unresolved_duplicate_keys,
             count(*) filter(where best_link_count>1) ambiguous_ccm from universe""")
        .df()
        .iloc[0]
        .astype(int)
        .to_dict()
    )
    db.close()
    return by_month, dict(
        **filings,
        **integrity,
        sector_status=sectors.status.value_counts().to_dict(),
        terminal_example=terminal_example,
        terminal_candidates=len(exits),
        missing_terminal_month_return=int(exits.missing_return.sum()),
        uncertain_exit_sensitivity=int(uncertain.sum()),
        terminal_scenario_means=exits[["ret", "minus30", "total_loss"]]
        .mean()
        .to_dict(),
    )
