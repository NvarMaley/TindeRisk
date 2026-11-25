"""Build deterministic chapter 7 descriptive research tables from chapter 6."""
from datetime import date,datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import fcntl

import duckdb
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.descriptive import summarize,distribution,time_diagnostics,covariance_matrix,longest_contiguous

DEST=ROOT/"data/processed/descriptive"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def metadata(db,path,name):
    count=db.execute("select count(*) from read_parquet(?)",[str(path)]).fetchone()[0]
    return {"dataset":name,"rows":count,"file_hash":digest(path)}


def build():
    source=returns_report(ROOT,date.today())
    if not source.get("datasets"):
        raise ValueError("Missing or invalid return snapshot")
    folder=ROOT/"data/processed/returns"/source["return_id"]
    DEST.mkdir(parents=True,exist_ok=True)
    with (DEST/"build.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(dir=DEST) as tmp, duckdb.connect() as db:
            stage=Path(tmp)
            db.execute("set threads=1")
            db.execute("""create temp table observations(source varchar, instrument varchar, frequency varchar,
                currency varchar, kind varchar, k int, start_date date,end_date date,value double)""")
            for row in source["datasets"]:
                if "total_returns" not in row:
                    continue
                name=row["dataset"]
                freq=row["frequency"]
                k={"daily":365 if name in ("btc","eth") else 252,"weekly":52,"monthly":12}.get(freq)
                for kind in ("price_return","total_return"):
                    if not row["price_returns" if kind=="price_return" else "total_returns"]:
                        continue
                    for currency in ("USD","CHF"):
                        column=kind+("_chf" if currency=="CHF" else "")
                        db.execute(f"""insert into observations select ?,instrument,?,?,?,?,start_date,end_date,{column}
                             from read_parquet(?)""",[name,freq,currency,kind,k,str(folder/f"{name}.parquet")])
            # Per-asset distributions and serial diagnostics preserve separate sources and currencies.
            rows=[]
            group_keys=["source","instrument","frequency","currency","kind"]
            for name, in db.execute("select distinct source from observations order by source").fetchall():
                frame=db.execute("select * from observations where source=? order by instrument,currency,kind,end_date,start_date",[name]).df()
                for key,group in frame.groupby(group_keys,sort=True):
                    values=group.value.to_numpy()
                    k=group.k.iloc[0]
                    stats=summarize(values,None if pd.isna(k) else int(k))
                    plots=distribution(values)
                    serial=time_diagnostics(longest_contiguous(group)) if key[2]!="irregular" else {}
                    rows.append(dict(zip(group_keys,key)) | {"first":str(group.end_date.min().date()),
                        "last":str(group.end_date.max().date()),"statistics":json.dumps(stats,sort_keys=True),
                        "distribution":json.dumps(plots,sort_keys=True),"time_diagnostics":json.dumps(serial,sort_keys=True)})
            path=stage/"asset_statistics.parquet"
            summaries=pd.DataFrame(rows)
            db.register("summary_rows",summaries)
            db.execute("copy (select * from summary_rows order by source,instrument,frequency,currency,kind) to ? (format parquet,compression zstd)",[str(path)])
            partitions=[metadata(db,path,"asset_statistics")]
            # Trailing windows, with exact period continuity and matched benchmark endpoints.
            path=stage/"rolling_features.parquet"
            db.execute("""copy (with benchmark as(select frequency,currency,start_date,end_date,value benchmark_return
                from observations where source in ('benchmark_daily','benchmark_daily_weekly','benchmark_monthly')
                and kind='total_return'),
              aligned as(select o.*,b.benchmark_return,
                case when lag(o.end_date) over(partition by o.source,o.instrument,o.currency,o.kind order by o.end_date)
                =o.start_date then 0 else 1 end gap
                from observations o left join benchmark b using(frequency,currency,start_date,end_date)
                where o.frequency in ('daily','weekly','monthly')),
              moving_stats as(select *,count(value) over w n,avg(value) over w m,stddev_samp(value) over w vol,
                count(benchmark_return) over w bn,covar_samp(value,benchmark_return) over w cov,
                var_samp(benchmark_return) over w bv,corr(value,benchmark_return) over w correlation,
                sum(gap) over g gaps
                from aligned window w as(partition by source,instrument,currency,kind order by end_date rows between 19 preceding and current row),
                g as(partition by source,instrument,currency,kind order by end_date rows between 18 preceding and current row))
              select source,instrument,frequency,currency,kind,start_date,end_date,value,20 window_periods,
                case when n=20 and gaps=0 then m end rolling_mean,
                case when n=20 and gaps=0 then vol end rolling_volatility,
                case when n=20 and gaps=0 then vol*sqrt(k) end annualized_volatility,
                case when n=20 and bn=20 and gaps=0 and bv>0 then cov/bv end rolling_beta,
                case when n=20 and bn=20 and gaps=0 and bv>0 and isfinite(correlation) then correlation end rolling_correlation
                from moving_stats order by source,instrument,currency,kind,end_date) to ? (format parquet,compression zstd)""",[str(path)])
            partitions.append(metadata(db,path,"rolling_features"))
            # Fixed training split; fit clipping and scale only on pre-2020 observations.
            path=stage/"cross_section.parquet"
            db.execute("""copy (with bounds as(select source,currency,kind,quantile_cont(value,.01) lo,quantile_cont(value,.99) hi
                from observations where end_date<=date '2019-12-31' and frequency in ('daily','weekly','monthly') group by all),
              trained as(select o.source,o.currency,o.kind,avg(least(greatest(o.value,b.lo),b.hi)) mu,
                stddev_samp(least(greatest(o.value,b.lo),b.hi)) sigma
                from observations o join bounds b using(source,currency,kind)
                where o.end_date<=date '2019-12-31' and o.value is not null group by all),
              valid as(select o.*,percent_rank() over(partition by o.source,o.currency,o.kind,o.start_date,o.end_date order by o.value) cross_section_rank
                from observations o where o.frequency in ('daily','weekly','monthly') and o.value is not null)
              select v.source,v.instrument,v.frequency,v.currency,v.kind,v.start_date,v.end_date,v.value,v.cross_section_rank,
                case when v.end_date>date '2019-12-31' and t.sigma>0
                then (least(greatest(v.value,b.lo),b.hi)-t.mu)/t.sigma end standardized_return,
                date '2019-12-31' training_cutoff
                from valid v left join bounds b using(source,currency,kind) left join trained t using(source,currency,kind)
                order by v.source,v.instrument,v.currency,v.kind,v.end_date) to ? (format parquet,compression zstd)""",[str(path)])
            partitions.append(metadata(db,path,"cross_section"))
            # Coherent covariance for each listed-product source on a common return interval.
            matrices=[]
            for name in ("etf_crsp_daily","etf_crsp_monthly","listed_daily"):
                frame=db.execute("""select instrument,start_date,end_date,value from observations
                    where source=? and currency='USD' and kind='total_return' and start_date is not null""",[name]).df()
                wide=frame.pivot(index=["start_date","end_date"],columns="instrument",values="value")
                result=covariance_matrix(wide.to_numpy())
                matrices.append({"source":name,"assets":list(wide.columns),"result":result})
            frame=db.execute("""select source||':'||instrument instrument,start_date,end_date,value from observations
                where source in ('listed_daily','btc','eth') and currency='USD'
                and kind='price_return' and start_date is not null""").df()
            wide=frame.pivot(index=["start_date","end_date"],columns="instrument",values="value")
            matrices.append({"source":"listed_crypto_daily_price","assets":list(wide.columns),
                             "result":covariance_matrix(wide.to_numpy())})
            # Matrices stay local, including their instrument identifiers.
            path=stage/"covariance_reference.json"
            path.write_text(json.dumps(matrices,sort_keys=True,allow_nan=False))
            partitions.append({"dataset":"covariance_reference","rows":len(matrices),"file_hash":digest(path),"extension":"json"})
            coverage=db.execute("""select source,frequency,count(distinct instrument) instruments,count(*) observations,
                count(value) valid,min(end_date) first,max(end_date) last from observations group by all order by source""").fetchall()
            groups=[dict(source=r[0],frequency=r[1],instruments=r[2],observations=r[3],valid=r[4],first=str(r[5]),last=str(r[6])) for r in coverage]
            identifier=hashlib.sha256(json.dumps([source["return_id"],partitions,groups],sort_keys=True).encode()).hexdigest()
            output=DEST/identifier
            output.mkdir(exist_ok=True)
            for path in stage.iterdir():
                target=output/path.name
                if target.exists():
                    if digest(target)!=digest(path):
                        raise ValueError("Descriptive snapshot conflict")
                else:
                    path.replace(target)
            report={"schema":"descriptive-v1","return_id":source["return_id"],"descriptive_id":identifier,
                "built_at":datetime.now(timezone.utc).isoformat(),"approved":False,"datasets":partitions,"sources":groups,
                "covariance_checks":[{"source":m["source"],"assets":len(m["assets"]),"observations":m["result"]["count"],"psd":m["result"]["psd"]} for m in matrices]}
            pending=stage/"report.json"
            pending.write_text(json.dumps(report,indent=2))
            pending.replace(DEST/"report.json")
    print(f"{len(rows):,} asset statistics; {sum(x['rows'] for x in partitions):,} output rows")


if __name__=="__main__":
    build()
