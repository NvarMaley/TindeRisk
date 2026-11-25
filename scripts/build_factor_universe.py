"""Local Chapter 10: dated scores, factor panels and catalogue exposures."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path
import fcntl
import hashlib
import json
import os
import sys
import tempfile

for variable in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
    os.environ[variable]="1"
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
import duckdb
import numpy as np
import pandas as pd
from riskmatch.analytics.descriptive_report import client_catalog
from riskmatch.analytics.factors import VERSION,TAXONOMY,PUBLISHED,zscore,neutralize,factor_portfolio,regression,pca_diagnostics
from riskmatch.market_data.returns import returns_report
from riskmatch.market_data.point_in_time import snapshot_report
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.analytics.volatility import factor_covariance,covariance_diagnostics
from riskmatch.analytics.risk_report import risk_batch_report
from riskmatch.analytics.forecast_fallback import _coupon_date


def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def save_frame(db,frame,path):
    db.register("output_frame",frame)
    db.execute("copy (select * from output_frame) to ? (format parquet,compression zstd)",[str(path)])
    db.unregister("output_frame")


def scores(db,pit,as_of):
    names=("stock_membership","stock_outcomes","ccm_links","fundamentals_annual")
    for n in names:
        db.execute(f"create view {n} as select * from read_parquet('{str(pit/(n+'.parquet')).replace(chr(39),chr(39)*2)}')")
    # A return ending at the ranking date is known only for the following interval.
    base=db.execute("""with past as(select instrument,observation_date,observed_return from stock_outcomes),
        joined as(select m.instrument,m.observation_date ranking_date,m.market_cap_source_units cap,
        m.reported_month_volume volume,p.observed_return previous_return
        from stock_membership m left join past p using(instrument,observation_date)),
        lagged as(select *,count(previous_return) over w n12,stddev_samp(previous_return) over w vol,
        lag(ranking_date,11) over(partition by instrument order by ranking_date) first12,
        count(previous_return) over w1 n11,product(1+previous_return) over w1 momentum
        from joined window w as(partition by instrument order by ranking_date rows between 11 preceding and current row),
        w1 as(partition by instrument order by ranking_date rows between 11 preceding and 1 preceding))
        select a.instrument,a.ranking_date,case when cap>0 then -ln(cap) end size,
        case when volume>0 then ln(volume) end liquidity,case when cap>0 then ln(cap) end log_cap,
        case when n12=12 and date_diff('month',first12,a.ranking_date)=11 then -vol end low_volatility,
        case when n11=11 and date_diff('month',first12,a.ranking_date)=11 then momentum-1 end momentum,
        o.observation_date end_date,o.observed_return next_return
        from lagged a left join stock_outcomes o on a.instrument=o.instrument and a.ranking_date=o.ranking_date
        where a.ranking_date<=? and (o.observation_date is null or o.observation_date<=?)
        order by a.ranking_date,a.instrument""",[as_of,as_of]).df()
    # Original SEC filing values, accepted strictly before ranking date.
    # Conflicting tag values or multiple active identifiers remain null.
    annual=db.execute("""with filing as(select instrument,f.observation_date,adsh,accepted,
        case when count(distinct value) filter(where tag='Assets' and qtrs=0)=1 then max(value) filter(where tag='Assets' and qtrs=0) end assets,
        case when count(distinct value) filter(where tag='Liabilities' and qtrs=0)=1 then max(value) filter(where tag='Liabilities' and qtrs=0) end liabilities,
        case when count(distinct value) filter(where tag='NetIncomeLoss' and qtrs=4)=1 then max(value) filter(where tag='NetIncomeLoss' and qtrs=4) end income,
        case when count(distinct value) filter(where tag='StockholdersEquity' and qtrs=0)=1 then max(value) filter(where tag='StockholdersEquity' and qtrs=0) end equity
        from fundamentals_annual f where uom='USD' and accepted is not null group by 1,2,3,4),
        links as(select m.instrument,m.observation_date ranking_date,min(l.instrument) gvkey
        from stock_membership m join ccm_links l on m.instrument=l.LPERMNO
        and m.observation_date>=l.observation_date and (l.valid_until_inclusive is null or m.observation_date<=l.valid_until_inclusive)
        where l.LINKTYPE in ('LC','LU') and l.LINKPRIM in ('P','C')
        group by 1,2 having count(distinct l.instrument)=1),
        ranked as(select l.instrument,l.ranking_date,f.assets,f.liabilities,f.income,f.equity,f.observation_date fiscal_date,f.accepted,
        row_number() over(partition by l.instrument,l.ranking_date,f.observation_date order by f.accepted desc,f.adsh desc) rn
        from links l join filing f on l.gvkey=f.instrument and cast(f.accepted as date)<l.ranking_date
        and f.observation_date<=l.ranking_date and date_diff('day',f.observation_date,l.ranking_date)<=1095),
        annual_history as(select *,lag(assets) over w prior_assets,lag(fiscal_date) over w prior_fiscal,
          row_number() over(partition by instrument,ranking_date order by fiscal_date desc) latest
          from ranked where rn=1 window w as(partition by instrument,ranking_date order by fiscal_date))
        select instrument,ranking_date,case when assets>0 and liabilities>=0 and income is not null
          then income/assets-liabilities/assets end quality,
        case when equity>0 and income is not null then income/equity end profitability_proxy,
        case when equity>0 then equity end book_equity,
        case when assets>0 and prior_assets>0 and date_diff('month',prior_fiscal,fiscal_date) between 9 and 15
            then 1-assets/prior_assets end investment,
        fiscal_date,accepted from annual_history where latest=1""").df()
    base=base.merge(annual,on=["instrument","ranking_date"],how="left",validate="one_to_one")
    base["ranking_date"]=pd.to_datetime(base.ranking_date)
    base["end_date"]=pd.to_datetime(base.end_date)
    # Rank ratio only: original market-cap units are not represented as dollars.
    base["value"]=base.book_equity/np.exp(base.log_cap)
    keys=("size","value","momentum","low_volatility","liquidity","quality","profitability_proxy","investment")
    previous={}; portfolios=[]; frames=[]
    for day,g in base.groupby("ranking_date",sort=True):
        g=g.copy()
        g["liquidity"]=neutralize(g.liquidity,g.log_cap)
        for key in keys:
            g[key+"_score"]=zscore(g[key])
            r=factor_portfolio(g.instrument.tolist(),g[key+"_score"],g.next_return,previous.get(key))
            if r:
                previous[key]=r.pop("weights")
                outcomes=g.end_date.dropna().unique()
                if len(outcomes)==1:
                    portfolios.append({"ranking_date":str(day.date()),"end_date":str(pd.Timestamp(outcomes[0]).date()),
                                       "factor":key,**r})
        frames.append(g[["instrument","ranking_date","accepted","fiscal_date",*([k+"_score" for k in keys])]])
    return pd.concat(frames),pd.DataFrame(portfolios)


def factor_panels(db,pit,portfolios,as_of):
    ff=db.execute("select instrument,observation_date,frequency,value from read_parquet(?) where observation_date<=?",[str(pit/"fama_french.parquet"),as_of]).df()
    ff["observation_date"]=pd.to_datetime(ff.observation_date)
    daily=ff[ff.frequency=="daily"].pivot(index="observation_date",columns="instrument",values="value").sort_index()
    monthly=ff[ff.frequency=="monthly"].pivot(index="observation_date",columns="instrument",values="value").sort_index()
    monthly.index=monthly.index.to_period("M").to_timestamp("M")
    # Monthly rate changes and CPI changes, ex-post exposures, never predictors.
    for source in ("dgs3mo","dgs2","dgs5","dgs10","cpiaucsl"):
        frame=db.execute("select observation_date,observed_value from read_parquet(?) where observation_date<=? order by observation_date",[str(pit/(source+".parquet")),as_of]).df()
        frame["observation_date"]=pd.to_datetime(frame.observation_date)
        series=frame.set_index("observation_date").observed_value.resample("ME").last()
        monthly[source]=series if source=="cpiaucsl" else series/100
    monthly["carry_proxy"]=monthly.dgs3mo.diff()
    monthly["term_proxy"]=monthly.dgs10.diff()
    monthly["curve_slope"]=(monthly.dgs10-monthly.dgs2).diff()
    monthly["curve_curvature"]=(2*monthly.dgs5-monthly.dgs2-monthly.dgs10).diff()
    monthly["inflation_proxy"]=monthly.cpiaucsl.pct_change(fill_method=None)
    if len(portfolios):
        p=portfolios.pivot(index="end_date",columns="factor",values="gross")
        p.index=pd.to_datetime(p.index).to_period("M").to_timestamp("M")
        for key in ("quality","low_volatility","liquidity"):
            monthly[key]=p[key] if key in p else np.nan
    return daily,monthly.drop(columns=["dgs3mo","dgs2","dgs5","dgs10","cpiaucsl"])


def prepare_asset(item,db,folder,daily,monthly,as_of):
    ident={k:item[k] for k in ("id","ticker","category")}
    for kind in ("total_return","price_return"):
        for frequency,panel in (("monthly",monthly),("daily",daily)):
            for s in sorted(item["series"],key=lambda x:x["last"],reverse=True):
                if s["frequency"]!=frequency or kind not in s["kinds"]:continue
                if frequency=="daily" and item["category"]=="crypto":continue
                frame=db.execute(f"""select start_date,end_date,{kind} value from read_parquet(?)
                   where instrument=? and end_date<=? and {kind} is not null order by end_date""",
                   [str(folder/(s["source"]+".parquet")),s["instrument"],as_of]).df()
                if frequency=="monthly":
                    frame=frame[frame.start_date.notna()]
                    frame=frame[(pd.to_datetime(frame.end_date).dt.to_period("M").astype(int)-pd.to_datetime(frame.start_date).dt.to_period("M").astype(int))==1]
                frame["factor_date"]=pd.to_datetime(frame.end_date)
                if frequency=="monthly":frame["factor_date"]=frame.factor_date.dt.to_period("M").dt.to_timestamp("M")
                frame=frame.merge(panel,left_on="factor_date",right_index=True,how="inner",validate="many_to_one")
                if frame[["value","Mkt-RF","RF"]].dropna().shape[0]<36:continue
                # use matched observations, report missing coverage; no interpolation.
                return ident|{"status":"ready","frequency":frequency,"kind":kind,"source":s["source"],
                    "instrument":s["instrument"],"frame":frame,"currency":"USD"}
    return ident|{"status":"unavailable","reason":"No sufficiently long matched regular USD factor history"}


def fit_asset(job):
    if job["status"]!="ready":return job
    f=job.pop("frame")
    specs={"capm":["Mkt-RF"],"ff3_subset":["Mkt-RF","SMB","HML"],
           "ff5":["Mkt-RF","SMB","HML","RMW","CMA"],"ff6":list(PUBLISHED)}
    if job["frequency"]=="monthly":
        specs["macro_sensitivity"]=["Mkt-RF","carry_proxy","term_proxy","curve_slope","curve_curvature","inflation_proxy"]
        specs["internal_styles"]=["Mkt-RF","quality","low_volatility","liquidity"]
    models={}; unavailable={}
    for name,columns in specs.items():
        try:
            matched=f[["end_date","value","RF",*columns]].dropna()
            models[name]=regression(matched.value-matched.RF,matched[columns],matched.end_date.tolist(),columns,job["frequency"])
            models[name]["implied_total_reference"]=models[name]["implied_expected_excess"]+float(matched.RF.iloc[:models[name]["split"]["train"]].mean())
        except (ValueError,KeyError,ArithmeticError,np.linalg.LinAlgError) as e:unavailable[name]=str(e)
    return job|{"status":"computed" if models else "unavailable","models":models,"unavailable":unavailable,
                "matched_factor_rows":len(f),"limitations":"Retrospective realized factor exposure; price-only targets are not total-return CAPM."}


def fixed_income_reference(job,estimate,db,pit):
    if not estimate:return job
    if job["category"]=="cash":
        return job|{"status":"analytical_reference","reference":{"carry_rate":estimate["value"],"as_of":estimate["as_of"],
            "limitations":"Indicative overnight SOFR; no equity-factor regression."}}
    if job["category"]!="treasury":return job
    cusip=job["id"].split(":",1)[1]
    terms=db.execute("""select instrument_type,coupon_rate_decimal,maturity from read_parquet(?)
                         where instrument=? limit 1""",[str(pit/"treasury_identity.parquet"),cusip]).fetchone()
    if not terms or terms[1] is None:return job
    kind,coupon,maturity=terms; mark=date.fromisoformat(estimate["as_of"]); y=estimate["value"]
    if maturity<=mark:return job
    if kind=="treasury_bill":
        mod=(maturity-mark).days/365/(1+y)
    else:
        dates=[];i=0
        while _coupon_date(maturity,6*i)>mark:
            dates.append(_coupon_date(maturity,6*i));i+=1
        prev=_coupon_date(maturity,6*i);dates.reverse()
        fraction=(dates[0]-mark).days/(dates[0]-prev).days
        periods=np.arange(len(dates))+fraction
        cash=np.full(len(dates),100*coupon/2);cash[-1]+=100
        pv=cash/(1+y/2)**periods
        mod=float((periods/2@pv)/pv.sum()/(1+y/2))
    return job|{"status":"analytical_reference","reference":{"yield":y,"modified_duration":mod,"yield_type":"real" if kind=="tips" else "nominal",
        "as_of":str(mark),"limitations":"Conditional clean-mark yield; local parallel-shift duration, not empirical factor beta or key-rate exposure."}}


def common_risk_matrix(db,folder,monthly,vector,dest,window_count=None):
    if not vector:return None
    maps=[]
    for asset in vector["assets"]:
        values=db.execute("""select start_date,end_date,total_return from read_parquet(?)
          where instrument=? and end_date<=? and total_return is not null and start_date is not null""",
          [str(folder/(asset["source"]+".parquet")),asset["instrument"],date.fromisoformat(vector["as_of"])]).fetchall()
        maps.append({(a,b):v for a,b,v in values if np.isfinite(v)})
    periods=sorted(set.intersection(*(set(m) for m in maps)))
    chain=[]
    for interval in periods:
        if chain and chain[-1][1]!=interval[0]:chain=[]
        chain.append(interval)
    if window_count:chain=chain[-window_count:]
    factor_dates=pd.DatetimeIndex([x[1] for x in chain]).to_period("M").to_timestamp("M")
    frame=monthly.reindex(factor_dates)[["RF",*PUBLISHED]].dropna()
    if len(frame)<60:return None
    keep=factor_dates.isin(frame.index)
    series=np.array([[m[p] for m in maps] for p in chain])[keep]
    excess=series-frame.RF.to_numpy()[:,None]; factors=frame[list(PUBLISHED)].to_numpy()
    a,b=int(.6*len(excess)),int(.8*len(excess))
    design=np.column_stack([np.ones(a),factors[:a]])
    beta=np.linalg.lstsq(design,excess[:a],rcond=None)[0]
    risk=factor_covariance(excess[:a],factors[:a])
    systematic=beta[1:].T@np.cov(factors[:a],rowvar=False,ddof=1)@beta[1:]
    diagonal=np.asarray(risk["diagonal_residual_covariance"]);full=np.asarray(risk["full_residual_covariance"])
    w=np.ones(len(maps))/len(maps); realized=(excess[b:]-excess[:a].mean(0))@w
    filename="common_factor_covariance.npz"
    np.savez_compressed(dest/filename,asset_ids=np.array([x["id"] for x in vector["assets"]]),beta=beta[1:].T,
        systematic=systematic,diagonal_residual=diagonal,full_residual=full)
    return {"file":filename,"assets":len(maps),"observations":len(excess),"as_of":vector["as_of"],"factors":list(PUBLISHED),
        "diagonal_diagnostics":covariance_diagnostics(diagonal),"full_diagnostics":covariance_diagnostics(full),
        "test_realized_variance":float(np.mean(realized**2)),"predicted_diagonal_variance":float(w@diagonal@w),
        "predicted_full_variance":float(w@full@w),"approved":False}


def build(as_of,workers):
    report=returns_report(ROOT,as_of); snapshot=snapshot_report(ROOT,as_of)
    if not report.get("datasets") or not snapshot.get("datasets"):raise ValueError("Verified return and PIT snapshots required")
    pit=ROOT/"data/processed/pit"/snapshot["snapshot_id"]; folder=ROOT/"data/processed/returns"/report["return_id"]
    catalogue=client_catalog(ROOT,as_of)["items"]; base=ROOT/"data/processed/factors";base.mkdir(parents=True,exist_ok=True)
    run=hashlib.sha256(json.dumps([report["return_id"],VERSION,as_of.isoformat(),[a["id"] for a in catalogue]]).encode()).hexdigest()
    dest=base/run;dest.mkdir(exist_ok=True)
    with (base/"build.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with duckdb.connect(config={"threads":2}) as db:
            score_frame,portfolios=scores(db,pit,as_of)
            save_frame(db,score_frame,dest/"scores.parquet")
            save_frame(db,portfolios,dest/"factor_portfolios.parquet")
            daily,monthly=factor_panels(db,pit,portfolios,as_of)
            save_frame(db,daily.reset_index(),dest/"daily_factors.parquet")
            save_frame(db,monthly.reset_index(),dest/"monthly_factors.parquet")
            print(f"Scores {len(score_frame)}; portfolio periods {len(portfolios)}",flush=True)
            forecast_meta=batch_report(ROOT,as_of)
            estimates={};vector=None
            if forecast_meta.get("status")=="complete":
                previous=ROOT/"data/processed/forecasts"/forecast_meta["run_id"]
                with (previous/"results.jsonl").open() as stream:
                    for line in stream:
                        row=json.loads(line)
                        if row.get("estimate"):estimates[row["id"]]=row["estimate"]
                vector=json.loads((previous/"common_monthly_total_return.json").read_text())
            jobs=[]
            for asset in catalogue:
                job=prepare_asset(asset,db,folder,daily,monthly,as_of)
                if job["status"]!="ready":job=fixed_income_reference(job,estimates.get(job["id"]),db,pit)
                jobs.append(job)
            risk_meta=risk_batch_report(ROOT,as_of)
            aligned=next((c for c in risk_meta.get("cohorts",[]) if c.get("cohort_type")=="chapter8_vector"),None)
            common_matrix=common_risk_matrix(db,folder,monthly,vector,dest,aligned["observations"] if aligned else None)
        print(f"Catalogue {len(jobs)}; matched factor candidates {sum(j['status']=='ready' for j in jobs)}",flush=True)
        rows=[]
        with (dest/"assets.jsonl").open("w") as stream,ProcessPoolExecutor(max_workers=workers) as pool:
            for row in pool.map(fit_asset,jobs,chunksize=4):
                rows.append(row);stream.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n")
                if len(rows)%100==0 or len(rows)==len(jobs):print(f"Exposure profiles {len(rows)}/{len(jobs)}",flush=True)
        # Train-only PCA on common published monthly factors.
        pca=pca_diagnostics(monthly[list(PUBLISHED)].dropna().to_numpy())
        pca["factor_names"]=list(PUBLISHED)
        counts=Counter(r["status"] for r in rows); models=Counter(); cats={}
        for row in rows:
            cats.setdefault(row["category"],Counter())[row["status"]]+=1
            models.update(row.get("models",{}).keys())
        score_counts={k:int(score_frame[k].count()) for k in score_frame if k.endswith("_score")}
        portfolio_summary={}
        # One common chronological evaluation grid, selected by availability of
        # score construction, then disclose missing realized legs separately.
        grid=portfolios.pivot(index="ranking_date",columns="factor",values="scored").dropna().sort_index()
        test_dates=grid.index[int(.8*len(grid)):]
        net_grid=portfolios.pivot(index="ranking_date",columns="factor",values="net").reindex(test_dates)
        complete_dates=net_grid.dropna().index
        for k,g in portfolios.groupby("factor"):
            g=g.sort_values("ranking_date");test=g[g.ranking_date.isin(test_dates)]
            clean=lambda v:float(v) if np.isfinite(v) else None
            portfolio_summary[k]={"periods":len(g),"valid_gross":int(g.gross.count()),"test_periods":len(test),
                "test_valid_net":int(test.net.count()),"test_mean_net":clean(test[test.ranking_date.isin(complete_dates)].net.mean()),
                "test_mean_rank_ic":clean(test.rank_ic.mean()),
                "test_average_turnover":clean(test.turnover.mean())}
        files={name:digest(dest/name) for name in ("scores.parquet","factor_portfolios.parquet","daily_factors.parquet","monthly_factors.parquet","assets.jsonl")}
        if common_matrix:files[common_matrix["file"]]=digest(dest/common_matrix["file"])
        meta={"status":"complete","approved":False,"version":VERSION,"as_of":as_of.isoformat(),"run_id":run,
              "data_version":report["return_id"],"catalogue_count":len(rows),"statuses":dict(counts),
              "by_category":{k:dict(v) for k,v in cats.items()},"by_model":dict(models),"taxonomy":TAXONOMY,
              "score_rows":len(score_frame),"score_coverage":score_counts,"portfolio_summary":portfolio_summary,"pca":pca,
              "common_factor_covariance":common_matrix,"portfolio_common_test":{"periods":len(test_dates),
                  "first":str(test_dates[0]) if len(test_dates) else None,
                  "last":str(test_dates[-1]) if len(test_dates) else None,"complete_net_periods":len(complete_dates)},
              "files":files}
        with tempfile.NamedTemporaryFile(mode="w",dir=base,delete=False) as stream:
            json.dump(meta,stream,allow_nan=False);tmp=Path(stream.name)
        tmp.replace(base/"report.json")
        print(json.dumps({"statuses":dict(counts),"models":dict(models),"scores":score_counts}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--as-of",type=date.fromisoformat,default=date.today())
    p.add_argument("--workers",type=int,default=4,choices=range(1,9));a=p.parse_args();build(a.as_of,a.workers)
