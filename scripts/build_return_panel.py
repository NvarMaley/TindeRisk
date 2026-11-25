"""Materialize research returns from the immutable chapter 5 snapshot."""
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import fcntl
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from riskmatch.market_data.point_in_time import snapshot_report

DEST = ROOT/"data/processed/returns"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def series_sql(table, reported, price="close", calendar="equity_calendar", daily=True,
               adjustment=None):
    """Keep source-separated return windows, with exact preceding sessions."""
    previous = "lag(observation_date) over w"
    valid = "start_date=expected_start" if daily else "date_diff('month',start_date,end_date)=1"
    expected_join = f"left join {calendar} c on a.end_date=c.session_date" if daily else ""
    expected = ",c.previous_day expected_start" if daily else ""
    extra=",ex_distribution_return" if adjustment=="crsp_monthly" else ""
    actions=""
    price_expr="close/prior_close-1"
    if adjustment=="crsp_monthly":
        price_expr="case when isfinite(ex_distribution_return) and ex_distribution_return>=-1 then ex_distribution_return end"
    elif adjustment=="crsp_daily":
        actions="""left join crsp_split_events s on b.instrument=s.instrument and b.end_date=s.observation_date"""
        price_expr="""case when coalesce(s.ambiguous,0)=0 and
          (reported is null or abs(close/prior_close*coalesce(s.factor,1)-1-reported)<=0.25)
          then close/prior_close*coalesce(s.factor,1)-1 end"""
    elif adjustment=="public":
        actions="""left join public_split_events s on b.instrument=s.instrument and b.end_date=s.observation_date"""
        # A known split is applied only when the raw close ratio is consistent
        # with that factor; ambiguous large moves are quarantined, not invented.
        price_expr="""case when s.events is null and abs(close/prior_close-1)<=0.5 then close/prior_close-1
          when s.events=1 and abs(close/prior_close*s.factor-1)<=0.5
            and abs(ln(close/prior_close*s.factor))<abs(ln(close/prior_close))
          then close/prior_close*s.factor-1
          when s.events=1 and abs(close/prior_close-1)<=0.5
            and abs(ln(close/prior_close))<abs(ln(close/prior_close*s.factor))
          then close/prior_close-1 end"""
    return f"""with a as (select instrument,observation_date end_date,{previous} start_date,
      {price} close,lag({price}) over w prior_close,{reported} reported{extra}
      from {table} window w as(partition by instrument order by observation_date)),
      b as(select a.*{expected} from a {expected_join})
      select b.instrument,start_date,end_date,
      case when {valid} and prior_close>0 and close>0 then {price_expr} end price_return,
      case when {valid} and isfinite(reported) and reported>=-1 then reported end total_return
      from b {actions}"""


def base_queries():
    return [
        ("etf_crsp_daily","daily","USD",series_sql("etf_crsp_daily","reported_return",adjustment="crsp_daily"),"reported total return; CRSP distribution-factor adjusted price return, ambiguous events excluded"),
        ("etf_crsp_monthly","monthly","USD",series_sql("etf_crsp_monthly","reported_return",daily=False,adjustment="crsp_monthly"),"reported total and ex-distribution returns"),
        ("listed_daily","daily","USD",series_sql("listed_daily","research_return",adjustment="public"),"research event-adjusted return; missing events stay missing"),
        ("stock_monthly","monthly","USD","select instrument,ranking_date start_date,observation_date end_date,cast(null as double) price_return,observed_return total_return from stock_outcomes","reported following-month cohort return"),
        ("stock_ticker_reference","daily","USD",series_sql("stock_ticker_reference","cast(null as double)",adjustment="public"),"split-reviewed price-only identity reference; unverified extreme moves excluded"),
        ("btc","daily","USD",series_sql("btc_usd","cast(null as double)",calendar="crypto_calendar"),"spot price return"),
        ("eth","daily","USD",series_sql("eth_usd","cast(null as double)",calendar="crypto_calendar"),"spot price return"),
        ("bill_marks","irregular","USD","select instrument,start_date,observation_date end_date,mark_return price_return,cast(null as double) total_return from bill_mark_returns","government marks before maturity"),
        ("benchmark_daily","daily","USD","select instrument,lag(observation_date) over(order by observation_date) start_date,observation_date end_date,cast(null as double) price_return,case when start_date is not null then value_weighted_return end total_return from wrds_daily_index","reported value-weighted index"),
        ("benchmark_monthly","monthly","USD","select instrument,lag(observation_date) over(order by observation_date) start_date,observation_date end_date,cast(null as double) price_return,case when start_date is not null then value_weighted_return end total_return from wrds_monthly_index","reported value-weighted index"),
        ("cash_sofr_index","irregular","USD","""with a as(select instrument,observation_date end_date,lag(observation_date) over(order by observation_date) start_date,observed_value idx,lag(observed_value) over(order by observation_date) prior from sofrindex)
         select 'USD_CASH' instrument,start_date,end_date,cast(null as double) price_return,case when prior>0 and idx>0 and date_diff('day',start_date,end_date)<=4 then idx/prior-1 end total_return from a""","SOFR index reference, not an investable security"),
        ("cash_sofr_accrual","irregular","USD","""with a as(select instrument,observation_date end_date,lag(observation_date) over(order by observation_date) start_date,lag(observed_value) over(order by observation_date) rate from sofr)
         select 'USD_CASH' instrument,start_date,end_date,cast(null as double) price_return,case when date_diff('day',start_date,end_date) between 1 and 4 then rate/100*date_diff('day',start_date,end_date)/360 end total_return from a""","ACT/360 indicative overnight accrual"),
        ("treasury_marks","irregular","USD","""with a as(select instrument,observation_date end_date,lag(observation_date) over w start_date,eod_price,lag(eod_price) over w prior from fedinvest_marks window w as(partition by instrument order by observation_date))
         select instrument,start_date,end_date,case when prior>0 then eod_price/prior-1 end price_return,cast(null as double) total_return from a""","valuation-only intervals, not realised total return"),
        ("nominal_bond_scenario","irregular","USD","""with a as(select instrument,observation_date end_date,
          lag(observation_date) over w start_date,eod_price,lag(eod_price) over w prior
          from fedinvest_marks where class in ('MARKET BASED NOTE','MARKET BASED BOND')
          window w as(partition by instrument order by observation_date)),
          b as(select a.*,p.contractual_accrued_per_100 prior_accrued,q.contractual_accrued_per_100 end_accrued
          from a join nominal_accrual p on a.instrument=p.instrument and a.start_date=p.observation_date
          join nominal_accrual q on a.instrument=q.instrument and a.end_date=q.observation_date),
          c as(select b.*,coalesce(sum(x.coupon_per_100+x.redemption_per_100),0) contractual_cash
          from b left join nominal_contractual_payments x on b.instrument=x.instrument and x.observation_date>b.start_date and x.observation_date<=b.end_date
          group by all)
          select instrument,start_date,end_date,eod_price/prior-1 price_return,
          case when prior+prior_accrued>0 then (eod_price+end_accrued+contractual_cash)/(prior+prior_accrued)-1 end total_return from c""",
          "conditional dirty-price scenario; assumes marks are clean and contractual cash is paid; unverified"),
    ]


def build_partition(db,stage,name,frequency,currency,query,method):
    # Every observation remains research-only until the upstream PIT gate is released.
    db.execute(f"""create or replace temp table returns_base as {query}""")
    db.execute("""create or replace temp table enriched as
        select a.*,case when total_return>-1 then ln(1+total_return) end log_total_return,
          case when price_return>-1 then ln(1+price_return) end log_price_return,
          case when f0.rate>0 and f1.rate>0 then (1+total_return)*f1.rate/f0.rate-1 end total_return_chf,
          case when f0.rate>0 and f1.rate>0 then (1+price_return)*f1.rate/f0.rate-1 end price_return_chf,
          cast(null as timestamptz) availability_time
        from returns_base a left join fx_usd_chf f0 on a.start_date=f0.observation_date
        left join fx_usd_chf f1 on a.end_date=f1.observation_date""")
    output=stage/f"{name}.parquet"
    db.execute("copy (select * from enriched order by instrument,end_date,start_date) to ? (format parquet, compression zstd)",[str(output)])
    rows,prices,totals,fx,fx_price,first,last=db.execute("""select count(*),count(price_return),count(total_return),count(total_return_chf),count(price_return_chf),min(end_date),max(end_date) from enriched""").fetchone()
    return {"dataset":name,"frequency":frequency,"base_currency":currency,"units":"decimal",
            "method":method,"rows":rows,"price_returns":prices,"total_returns":totals,
            "chf_total_returns":fx,"chf_price_returns":fx_price,"missing_total_returns":rows-totals,"first":str(first),"last":str(last),
            "file_hash":digest(output)}


def aggregate_query(path,calendar,frequency):
    period="week" if frequency=="weekly" else "month"
    path=str(path).replace("'","''")
    return f"""with expected as(
      select date_trunc('{period}',session_date) period_start,min(previous_day) start_date,
      max(session_date) end_date,count(*) expected_count
      from {calendar} group by 1),
      eligible as(select *,lead(period_start) over(order by period_start) next_period from expected),
      observed as(select a.instrument,e.start_date,e.end_date,e.expected_count,
      count(a.price_return) n_price,count(a.total_return) n_total,
      product(1+a.price_return)-1 price_return,product(1+a.total_return)-1 total_return
      from read_parquet('{path}') a join eligible e on date_trunc('{period}',a.end_date)=e.period_start
      where e.next_period is not null group by 1,2,3,4)
      select instrument,start_date,end_date,case when n_price=expected_count then price_return end price_return,
      case when n_total=expected_count then total_return end total_return from observed"""


def main():
    snapshot=snapshot_report(ROOT,date.today())
    if not snapshot.get("datasets"):
        raise ValueError("Missing or invalid PIT snapshot")
    source=ROOT/"data/processed/pit"/snapshot["snapshot_id"]
    DEST.mkdir(parents=True,exist_ok=True)
    with (DEST/"build.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(dir=DEST) as tmp, duckdb.connect() as db:
            stage=Path(tmp)
            db.execute("set threads=1")
            names=("etf_crsp_daily","etf_crsp_monthly","listed_daily","stock_outcomes","stock_refresh_ticker_reference","stock_refresh_identity","btc-usd","eth-usd","fx_usd_chf","bill_mark_returns","wrds_daily_index","wrds_monthly_index","sofrindex","sofr","fedinvest_marks","us_equity_sessions","cpiaucsl","fama_french","nominal_accrual","nominal_contractual_payments","wrds_distributions","split")
            for name in names:
                path=str(source/f"{name}.parquet").replace("'","''")
                db.execute(f"create view {name.replace('-','_')} as select * from read_parquet('{path}')")
            db.execute("""create temp table equity_calendar as with d as(select observation_date session_date from wrds_daily_index union select observation_date session_date from us_equity_sessions)
                select session_date,lag(session_date) over(order by session_date) previous_day from d""")
            db.execute("""create temp table crypto_calendar as select session_date::date session_date,(session_date-interval 1 day)::date previous_day
                from generate_series(date '2015-01-01',date '2026-11-23',interval 1 day) x(session_date)""")
            db.execute("""create temp view stock_ticker_reference as select a.* from stock_refresh_ticker_reference a
                where exists(select 1 from stock_refresh_identity b where b.snapshot_ticker=a.instrument)""")
            db.execute("""create temp table crsp_split_events as
                select instrument,observation_date,
                product(case when distype='FRS' and disdetailtype in ('STKSPL','STKDIV') and disfacpr>-1 then 1+disfacpr else 1 end) factor,
                count(*) filter(where disfacpr!=0 and not (distype='FRS' and disdetailtype in ('STKSPL','STKDIV') and disfacpr>-1)) ambiguous
                from wrds_distributions where disfacpr!=0 group by 1,2""")
            db.execute("""create temp table public_split_events as select instrument,observation_date,
                count(*) events,product(to_factor/for_factor) factor from split group by 1,2""")
            rows=[build_partition(db,stage,*spec) for spec in base_queries()]
            for name in ("etf_crsp_daily","listed_daily","stock_ticker_reference","btc","eth","benchmark_daily"):
                calendar="crypto_calendar" if name in ("btc","eth") else "equity_calendar"
                for frequency in ("weekly","monthly"):
                    rows.append(build_partition(db,stage,f"{name}_{frequency}",frequency,"USD",
                        aggregate_query(stage/f"{name}.parquet",calendar,frequency),"compounded complete session windows"))
            # CPI and RF are ex-post reference values by matching observation month.
            db.execute("""create temp table monthly_reference as with cpi as(
                select observation_date,observed_value,lag(observed_value) over(order by observation_date) previous,
                lag(observation_date) over(order by observation_date) previous_date from cpiaucsl),
                rf as(select observation_date,value from fama_french where instrument='RF' and frequency='monthly')
                select c.observation_date,case when c.previous>0 and date_diff('month',previous_date,c.observation_date)=1 then c.observed_value/c.previous-1 end inflation,
                       rf.value risk_free_return from cpi c left join rf on date_trunc('month',rf.observation_date)=c.observation_date""")
            output=stage/"monthly_real_excess.parquet"
            db.execute("""create temp table monthly_returns_all(source varchar,instrument varchar,start_date date,end_date date,
                return_kind varchar, nominal_return double)""")
            for row in rows:
                if row["frequency"]!="monthly":
                    continue
                name=row["dataset"]
                field="total_return" if row["total_returns"] else "price_return"
                db.execute(f"""insert into monthly_returns_all select ?,instrument,start_date,end_date,?,{field}
                    from read_parquet(?)""",[name,field,str(stage/f"{name}.parquet")])
            db.execute("""copy (select a.*,r.inflation,r.risk_free_return,
                case when r.inflation>-1 then (1+a.nominal_return)/(1+r.inflation)-1 end ex_post_real_return,
                a.nominal_return-r.risk_free_return excess_return
                from monthly_returns_all a left join monthly_reference r on date_trunc('month',a.end_date)=r.observation_date
                where a.start_date is null or date_diff('month',a.start_date,a.end_date)=1
                order by a.source,a.instrument,a.end_date) to ? (format parquet,compression zstd)""",[str(output)])
            count,real,excess=db.execute("select count(*),count(ex_post_real_return),count(excess_return) from read_parquet(?)",[str(output)]).fetchone()
            rows.append({"dataset":"monthly_real_excess","frequency":"monthly","base_currency":"USD","units":"decimal",
                         "method":"latest-vintage ex-post CPI and monthly factor risk-free reference","rows":count,"real_returns":real,"excess_returns":excess,"file_hash":digest(output)})
            for name,left,right in (
                ("etf_monthly_reconciliation","etf_crsp_daily_monthly","etf_crsp_monthly"),
                ("sofr_reconciliation","cash_sofr_accrual","cash_sofr_index"),
            ):
                output=stage/f"{name}.parquet"
                db.execute("""copy (select a.instrument,a.start_date,a.end_date,a.total_return calculated,
                    b.total_return reference,a.total_return-b.total_return difference
                    from read_parquet(?) a join read_parquet(?) b using(instrument,start_date,end_date)
                    where a.total_return is not null and b.total_return is not null
                    order by a.instrument,a.end_date,a.start_date) to ? (format parquet,compression zstd)""",
                    [str(stage/f"{left}.parquet"),str(stage/f"{right}.parquet"),str(output)])
                count,matches,rounded,maximum=db.execute("select count(*),count(*) filter(where abs(difference)<=1e-6),count(*) filter(where abs(difference)<=1e-5),max(abs(difference)) from read_parquet(?)",[str(output)]).fetchone()
                rows.append({"dataset":name,"frequency":"monthly" if name.startswith("etf") else "irregular","base_currency":"USD","units":"decimal",
                    "method":"exact interval cross-check; absolute tolerance 1e-6","rows":count,"matched":matches,
                    "matched_at_1e_5":rounded,"max_absolute_difference":maximum,"file_hash":digest(output)})
            db.execute("""create temp table return_samples(source varchar,instrument varchar,frequency varchar,
                periods_per_year int,return_kind varchar,start_date date,end_date date,observed_return double)""")
            for row in rows:
                name=row["dataset"]
                frequency=row["frequency"]
                if frequency not in ("daily","weekly","monthly") or "total_returns" not in row:
                    continue
                k={"daily":365 if name in ("btc","eth") else 252,"weekly":52,"monthly":12}[frequency]
                for field in ("price_return","total_return"):
                    db.execute(f"""insert into return_samples select ?,instrument,?,?,?,start_date,end_date,{field}
                        from read_parquet(?) where {field} is not null""",
                        [name,frequency,k,field,str(stage/f"{name}.parquet")])
            output=stage/"return_means.parquet"
            db.execute("""copy (with ordered as(select *,lag(end_date) over(partition by source,instrument,return_kind order by end_date) prior_end
                from return_samples), stats as(select source,instrument,frequency,periods_per_year,return_kind,
                min(start_date) start_date,max(end_date) end_date,count(*) observations,avg(observed_return) arithmetic_mean,
                count(*) filter(where observed_return=-1) wipeouts,
                sum(case when observed_return>-1 then ln(1+observed_return) else 0 end) log_growth,
                count(*) filter(where prior_end is not null and start_date is distinct from prior_end) gaps
                from ordered group by all)
                select source,instrument,frequency,periods_per_year,return_kind,start_date,end_date,observations,arithmetic_mean,
                case when wipeouts>0 then -1 else exp(log_growth/observations)-1 end geometric_mean,
                case when gaps=0 and observations>=periods_per_year then
                    case when wipeouts>0 then -1 else exp(log_growth*periods_per_year/observations)-1 end end annualized_geometric,
                case when gaps=0 and date_diff('day',start_date,end_date)>=365 then
                    case when wipeouts>0 then -1 else exp(log_growth*365/date_diff('day',start_date,end_date))-1 end end realized_cagr,
                gaps from stats order by source,instrument,return_kind) to ? (format parquet,compression zstd)""",[str(output)])
            count,annualized=db.execute("select count(*),count(annualized_geometric) from read_parquet(?)",[str(output)]).fetchone()
            rows.append({"dataset":"return_means","frequency":"mixed","base_currency":"USD","units":"decimal",
                "method":"arithmetic and geometric means; annualization only for continuous observed windows",
                "rows":count,"annualized_means":annualized,"file_hash":digest(output)})
            identifier=hashlib.sha256(json.dumps([snapshot["snapshot_id"],rows],sort_keys=True).encode()).hexdigest()
            folder=DEST/identifier
            folder.mkdir(exist_ok=True)
            for path in stage.glob("*.parquet"):
                target=folder/path.name
                if target.exists():
                    if digest(target)!=digest(path):
                        raise ValueError("Return partition hash conflict")
                else:
                    path.replace(target)
            report={"schema":"returns-v1","snapshot_id":snapshot["snapshot_id"],"return_id":identifier,
                    "built_at":datetime.now(timezone.utc).isoformat(),"approved":False,"datasets":rows,
                    "reason":"upstream_availability_and_return_reconciliation_pending"}
            temp=stage/"report.json"
            temp.write_text(json.dumps(report,indent=2))
            temp.replace(DEST/"report.json")
    print(f"{len(rows)} return partitions; {sum(r['rows'] for r in rows):,} rows")


if __name__=="__main__":
    main()
