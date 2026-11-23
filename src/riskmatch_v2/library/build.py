"""Build the private Parquet research catalogue and publish non-reconstructive summaries."""
from datetime import date
from hashlib import file_digest, sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from ..benchmark import write_json
from ..reference import study
from .controls import disposition, exclusion_status, exposure, identity_at, visible
from .sources import SECTORS, checked, crsp, holdings_tables, save, source_tables
from .statistics import sheet

RAW = Path("data/local/4/raw")
DEST = Path("data/local/4")
REPORT = Path("reports/04-catalogue")
US = "country_flag='Y' AND security_type='EQTY' AND subtype='COM' AND share_type='NS' AND exchange IN ('N','A','Q')"
WINDOWS = (1,3,5,10)


def etf_analysis(prices, fx, end, stage):
    panel = {}
    sheets = []
    reported = {}
    for ticker,frame in prices.groupby("symbol"):
        series=frame.set_index("day").adjusted.loc[:end].sort_index()
        eom=series.groupby(series.index.to_period("M")).tail(1)
        rates=fx.reindex(eom.index)
        local=eom.pct_change(fill_method=None)
        chf=(eom*rates).pct_change(fill_method=None)
        panel[ticker]={day.date():value for day,value in chf.dropna().items()}
        reported[ticker]=chf
        for years in WINDOWS:
            n=12*years
            x=sheet(n,local.iloc[-n:],rates.iloc[-n-1:],eom.index[-n-1:].values)
            sheets.append(dict(id=frame.id.iloc[0],symbol=ticker,years=years,
                               start=str(eom.index[-n-1].date()),end=end,**x))
    monthly=pd.DataFrame(reported)
    for years in WINDOWS:
        sample=monthly.tail(years*12).dropna()
        for method in ("pearson","spearman"):
            sample.corr(method=method).to_parquet(stage/f"funds_{years}a_{method}.parquet")
        (sample.cov()*12).to_parquet(stage/f"funds_{years}a_covariance.parquet")
    pd.DataFrame(sheets).to_parquet(stage/"fund_sheets.parquet",index=False)
    historical,_=study(panel,json.loads(Path("config/references-1.4.json").read_bytes()))
    previous=json.loads(Path("reports/01-4-references/resultats.json").read_bytes())["periods"]
    if len(previous)!=len(historical):
        raise ValueError("Number of periods different from benchmark")
    for a,b in zip(historical,previous,strict=True):
        if (a["start"],a["end"],a["mode"])!=(b["start"],b["end"],b["mode"]) or not np.isclose(a["final_chf"],b["final_chf"],rtol=1e-11):
            raise ValueError("Independent approximation of the unconcluded benchmark")
    return pd.DataFrame(sheets),monthly,historical


def stock_analysis(con,stage,fx):
    con.register("fxdata",pd.DataFrame({"day":fx.index,"fx":fx.to_numpy()}))
    con.execute("""CREATE TEMP TABLE calendar AS SELECT last_day(day) AS month_end,max(day) AS trading_day
                   FROM months GROUP BY 1""")
    con.execute(f"""CREATE TEMP TABLE stocks AS SELECT m.*, f.fx,
        CASE WHEN m.previous_day=prev.trading_day AND m.day=cur.trading_day AND m.local_return>=-1
             THEN m.local_return END AS usd,
        (1+usd)*f.fx/p.fx-1 AS chf
        FROM months m LEFT JOIN fxdata f ON f.day=m.day LEFT JOIN fxdata p ON p.day=m.previous_day
        LEFT JOIN calendar cur ON cur.month_end=last_day(m.day)
        LEFT JOIN calendar prev ON prev.month_end=last_day(m.day-INTERVAL '1 month')
        WHERE m.variants=1 AND {US}""")
    con.sql("""SELECT permno,day,previous_day,usd,chf,fx,del_flag,
                   CASE WHEN usd IS NULL THEN 'RENDEMENT_OU_BASE_INVALIDE' WHEN fx IS NULL THEN 'FX_ABSENT'
                        WHEN chf IS NULL THEN 'BASE_FX_ABSENTE' ELSE 'OK' END AS reason FROM stocks""").write_parquet(str(stage/"stock_returns.parquet"),compression="zstd")
    calendar=pd.DatetimeIndex(con.sql("SELECT trading_day FROM calendar ORDER BY trading_day").df().trading_day)
    # Missing pre-sample dates may produce partial sheets but never synthetic zero returns.
    dates=calendar.values.astype("datetime64[D]")
    fx_vec=fx.reindex(calendar).to_numpy()
    index={v:i for i,v in enumerate(dates)}
    records=[]
    for bucket, in con.sql("SELECT DISTINCT permno//5000 FROM stocks ORDER BY 1").fetchall():
        data=con.sql(f"SELECT permno,day,usd FROM stocks WHERE permno//5000={int(bucket)} ORDER BY permno,day").df()
        for permno,group in data.groupby("permno",sort=False):
            days=group.day.values.astype("datetime64[D]")
            valid=np.isin(days,dates)
            if not valid.any():
                continue
            indices=np.array([index[v] for v in days[valid]])
            last=indices[-1]
            local=np.full(121,np.nan)
            offsets=indices-last+120
            keep=offsets>=0
            local[offsets[keep]]=group.usd.to_numpy()[valid][keep]
            for years in WINDOWS:
                n=12*years
                start=last-n
                ix=np.arange(start,last+1)
                ds=np.full(n+1,np.datetime64("NaT"),dtype="datetime64[D]")
                fs=np.full(n+1,np.nan)
                ds[ix>=0]=dates[ix[ix>=0]]
                fs[ix>=0]=fx_vec[ix[ix>=0]]
                stats=sheet(n,local[-n:],fs,ds)
                records.append(dict(permno=int(permno),years=years,start=None if start<0 else str(dates[start]),
                                    end=str(dates[last]),**stats))
    all_sheets=pd.DataFrame(records)
    all_sheets.to_parquet(stage/"stock_sheets.parquet",index=False,compression="zstd")
    return all_sheets


def registry(con,instruments,sources,cutoff):
    # Preserve every source security, even those with only quarantined observations.
    entries=con.sql("""SELECT permno,min(day) AS first_seen,max(day) AS last_seen,
                              min(security_from) AS entry,max(security_end) AS vendor_end FROM raw GROUP BY permno""").df()
    latest=con.sql(f"""SELECT *, ({US}) AS in_scope FROM months WHERE variants=1
                      QUALIFY row_number() OVER(PARTITION BY permno ORDER BY day DESC)=1""").df()
    for r in entries.merge(latest,on="permno",how="left").itertuples():
        known=pd.notna(r.day)
        local=lambda v: str(v)[:10] if pd.notna(v) else None
        cls="action" if known and r.in_scope else "autre_CRSP"
        instruments.append(dict(id=f"PERMNO:{r.permno}",symbol=r.ticker if known else None,
                                name=r.issuer if known else None,issuer=f"PERMCO:{int(r.permco)}" if known and pd.notna(r.permco) else None,
                                role="instrument" if cls=="action" else "source pending review",asset_class=cls,
                                exchange=r.exchange if known else None,currency="USD",calendar="Monthly CRSP",
                                exposure="US" if cls=="action" else None,source="crsp_msf.csv",entry=local(r.entry),
                                exit=local(r.vendor_end) if local(r.vendor_end) and local(r.vendor_end)<cutoff else None,
                                first_seen=local(r.first_seen),last_seen=local(r.last_seen),available=sources["crsp_msf.csv"]["retrieved"]))
    return latest


def covariance_stocks(con, monthly, stage, cutoff):
    data=con.sql("""SELECT permno,day,chf FROM stocks WHERE day BETWEEN DATE '2023-01-01' AND DATE '2025-12-31'
                    AND permno IN (SELECT permno FROM stocks WHERE day=DATE '2025-12-31' AND trading='A')""").df()
    wide=data.pivot(index="day",columns="permno",values="chf")
    wide.columns=["PERMNO:"+str(x) for x in wide.columns]
    combined=monthly.reindex(wide.index).join(wide).loc[:cutoff]
    # Keep the complete-case universe explicit and store all exclusions for this diagnostic.
    missing=combined.isna().sum()
    missing.rename("missing_months").to_frame().to_parquet(stage/"covariance_coverage.parquet")
    full=combined.loc[:,missing==0]
    returns=full.to_numpy()
    cov=np.cov(returns,rowvar=False)*12
    sd=np.sqrt(np.diag(cov))
    with np.errstate(invalid="ignore",divide="ignore"):
        corr=cov/np.outer(sd,sd)
    np.savez_compressed(stage/"universe_covariance.npz",ids=np.array(full.columns,dtype=str),
                        dates=np.array(full.index.strftime("%Y-%m-%d")),covariance=cov,pearson=corr)
    return dict(months=len(full),series=full.shape[1],excluded=int((missing>0).sum()))


def assemble(stage,policy,sources):
    for filename,src in sources.items():
        checked(RAW/filename,src["sha256"])
    lock=json.loads(Path("config/import-2026-11-23.json").read_bytes())
    instruments,prices,fx,provenance=source_tables(lock,Path("data/local/1.3/raw"),stage)
    for s in sources.values():
        provenance.append(dict(**s,rights="Use local search. Private individual data."))
    save(pd.DataFrame(provenance),stage,"sources")
    holdings,bonds=holdings_tables(sources,RAW)
    save(holdings,stage,"holdings")
    instruments.extend(bonds)
    for key,role,cls,ccy in [("DCOILWTICO","factor","Spot oil","USD"),("DGS10","factor","U.S. Treasury Rate","USD"),
                             ("DEXSZUS","factor","change","CHF/USD"),("CASH-CHF","source pending review","cash","CHF"),
                             ("REF-60-40","benchmark","internal reference","CHF")]:
        instruments.append(dict(id=key,symbol=key,name=key,role=role,asset_class=cls,currency=ccy))
    for indicator in ("CPIAUCSL","INDPRO","UNRATE"):
        instruments.append(dict(id=indicator,symbol=indicator,name=indicator,role="factor",
                                asset_class="macro",source="macro_releases.parquet"))
    funds,monthly,benchmark=etf_analysis(prices,fx,policy["comparison_end"],stage)
    con=crsp(stage,RAW/"crsp_msf.csv")
    stocks=stock_analysis(con,stage,fx)
    cutoff=policy["equity_replay_end"]
    latest=registry(con,instruments,sources,cutoff)
    inventory=pd.DataFrame(instruments)
    assert inventory.id.is_unique
    save(inventory,stage,"instruments")
    covariance=covariance_stocks(con,monthly,stage,cutoff)
    stats=decisions(con,stage,inventory,latest,stocks,funds,fx,policy)
    day=policy["decision_utc"]
    mix=exposure({"SPY":.50,"XLK":.30,"AAPL":.20},holdings,{"AAPL":"CUSIP6:037833"},day)
    cover=[]
    for t in sorted(prices.symbol.unique()):
        r=exposure({t:1},holdings,{},day)
        cover.append(dict(fund=t,assigned_net=1-r["unknown_net"],unknown_gross=r["unknown_gross"]))
    ex=holdings[holdings.day.le(day[:10]) & (pd.to_datetime(holdings.available,utc=True)<=pd.Timestamp(day))]
    ex=ex.copy()
    # Use sector memberships disclosed by the decision time and for the same holdings date.
    sector_map=ex.dropna(subset=["security","sector"]).groupby(["day","security"]).sector.agg(
        lambda v: v.iloc[0] if v.nunique()==1 else None)
    ex["sector"]=ex.sector.fillna(pd.Series(sector_map.reindex(
        pd.MultiIndex.from_frame(ex[["day","security"]])).to_numpy(),index=ex.index))
    for dim in ("security","issuer","sector","currency"):
        ex.groupby(["fund",dim],dropna=False).weight.sum().to_frame().to_parquet(stage/f"concentration_{dim}.parquet")
    gov=ex[ex.issuer.eq("US-TREASURY")].copy()
    gov["duration_weighted"]=gov.weight*gov.duration
    gov.groupby("fund")[["weight","duration_weighted"]].sum().to_parquet(stage/"fund_bond_sensitivity.parquet")
    apple=ex[ex.issuer.eq("CUSIP6:037833")].groupby("fund").weight.sum()
    manual=.20+.5*apple["SPY"]+.3*apple["XLK"]
    assert np.isclose(manual,mix["issuers"]["CUSIP6:037833"])
    summary=dict(version=policy["version"],decision_utc=day,inventory=inventory.asset_class.value_counts().to_dict(),
                 crsp_rows=con.sql("SELECT count(*) FROM raw").fetchone()[0],
                 stock_months=con.sql("SELECT count(*) FROM months WHERE variants=1").fetchone()[0],
                 quarantined=pq.ParquetFile(stage/"stock_quarantine.parquet").metadata.num_rows,
                 stock_sheets=len(stocks),stock_ids=stocks.permno.nunique(),fund_sheets=len(funds),
                 etf_sessions=len(prices),fund_window_summary=window_summary(funds),stock_window_summary=window_summary(stocks),
                 covariance=covariance,eligibility=stats,holdings_rows=len(holdings),coverage=cover,
                 overlap=dict(direct=.2,via_spy=float(.5*apple["SPY"]),via_xlk=float(.3*apple["XLK"]),
                              total=manual,unassigned_net=mix["unknown_net"],unassigned_gross=mix["unknown_gross"],
                              hard_exclusion=exclusion_status(mix,{"CUSIP6:037833"},True)),
                 comparison=[{k:r[k] for k in ("mode","start","end","months","final_chf","cagr","fees_chf")}
                             for r in benchmark if r["end"]==policy["comparison_end"]])
    summary["daily_alignment"]=prices.reason.value_counts().to_dict()
    summary["stock_alignment"]=con.sql(f"SELECT reason,count(*) AS n FROM read_parquet(?) GROUP BY reason",
                                         params=[str(stage/"stock_returns.parquet")]).df().set_index("reason").n.to_dict()
    events = pd.read_parquet(stage/"events.parquet")
    summary["events"] = events.kind.value_counts().to_dict()
    quotes = prices.sort_values(["id", "day"]).copy()
    quotes["previous_close"] = quotes.groupby("id").close.shift()
    quotes["day"] = quotes.day.dt.strftime("%Y-%m-%d")
    dividends = events[events.kind.eq("dividends")].merge(
        quotes[["id", "day", "previous_close", "close", "return_usd"]], on=["id", "day"],
        how="left", validate="many_to_one")
    # The vendor's close is split-adjusted. A second split adjustment would count it twice.
    dividends["reconstructed"] = (dividends.close + dividends.cash) / dividends.previous_close - 1
    dividends["gap_bp"] = (dividends.reconstructed - dividends.return_usd) * 10000
    dividends["status"] = np.select([dividends.gap_bp.isna(), dividends.gap_bp.abs() > 10],
                                     ["BASE_ABSENTE", "ECART_SUPERIEUR_10_PB"], default="RAPPROCHE")
    dividends.to_parquet(stage/"dividend_audit.parquet", index=False)
    summary["dividend_audit"] = dividends.status.value_counts().to_dict()
    summary["timing"]=information_calendar(stage,policy,sources)
    con.close()
    return summary


def window_summary(frame):
    return [dict(years=int(n), sheets=len(rows), complete=int(rows.full_sample.sum()),
                 compound=int(rows.cumulative.notna().sum()), median_observations=float(rows.observations.median()))
            for n,rows in frame.groupby("years")]


def decisions(con,stage,inventory,latest,stocks,funds,fx,policy):
    risk=stocks[stocks.years.eq(3)].set_index("permno").observations
    fobs=funds[funds.years.eq(3)].set_index("symbol").observations
    stocklast=latest.set_index("permno")
    lastfx=str(fx.dropna().index[-1].date())
    decisions=[]
    for q in inventory.to_dict("records"):
        ended=pd.notna(q.get("exit"))
        day=q.get("last_seen")
        history=int(fobs.get(q.get("symbol"),0)) if str(q["id"]).startswith("ETF-") else 0
        if str(q["id"]).startswith("PERMNO:"):
            perm=int(q["id"].split(":")[1])
            history=int(risk.get(perm,0))
            day=str(stocklast.at[perm,"price_day"])[:10] if perm in stocklast.index else None
        reasons=disposition(dict(role=q["role"],currency=q.get("currency"),ended=ended,price_day=day,fx_day=lastfx,
                            identified=pd.notna(q.get("issuer")),mandate_scope=q.get("exposure") in ("US","or"),
                            available=q.get("available"),history=history,distinct=q["role"]=="instrument",
                            class_terms=q["asset_class"] in ("action","fonds_tresor","fonds_actions","vehicule_or")),policy)
        decisions.append(dict(id=q["id"],asset_class=q["asset_class"],price_day=day,fx_day=lastfx,
                              history_months=history,date=policy["decision_utc"],eligible=not reasons,reasons="|".join(reasons)))
    d=pd.DataFrame(decisions)
    d.to_parquet(stage/"decision.parquet",index=False)
    # Economic history as observed retrospectively, separately from decision-time availability.
    replay=con.sql("""SELECT permno,day,previous_day,ticker,trading,price,local_return,usd,chf,del_flag,exit_payment
                      FROM stocks WHERE day=DATE '2025-12-31'""").df()
    replay["available"]=inventory.loc[inventory.id.str.startswith("PERMNO:"),"available"].dropna().iloc[0]
    replay["known_in_2025"]=pd.to_datetime(replay.available,utc=True)<=pd.Timestamp("2025-12-31T21:00:00Z")
    replay.to_parquet(stage/"replay_2025.parquet",index=False)
    ident=con.sql("SELECT permno,ticker,id_from,id_to FROM identifiers WHERE ticker='AAPL'").df()
    example=identity_at(ident,"AAPL",policy["equity_replay_end"])
    apple=replay[replay.permno.eq(example)].iloc[0]
    current=d[d.id.eq(f"PERMNO:{example}")].iloc[0]
    return dict(example=dict(ticker="AAPL",recorded_active_2025=bool(apple.trading=="A"),
                             known_in_2025=bool(apple.known_in_2025),eligible_2026=bool(current.eligible),
                             reasons_2026=current.reasons.split("|")),
                total=len(d),eligible=int(d.eligible.sum()),by_class=d.groupby("asset_class").eligible.agg(["size","sum"]).to_dict("index"),
                replay_rows=len(replay), replay_active=int((replay.trading=="A").sum()),
                replay_verified_at_date=int(replay.known_in_2025.sum()))


def information_calendar(stage,policy,sources):
    rows=[]
    for series in ("DCOILWTICO","DGS10"):
        df=pd.read_csv(RAW/f"{series}.csv")
        frame=pd.DataFrame(dict(series=series,day=df.iloc[:,0],value=pd.to_numeric(df[series],errors="coerce"),
                                available=sources[f"{series}.csv"]["retrieved"],published=None))
        rows.append(frame)
    macro=pd.read_parquet(RAW/"macro_releases.parquet")
    macro=macro.rename(columns=dict(observation_date="day",available_at="available",published_at="published"))
    panel=pd.concat([*rows,macro],ignore_index=True)
    panel["day"]=pd.to_datetime(panel.day,format="mixed").dt.strftime("%Y-%m-%d")
    panel["available"]=pd.to_datetime(panel.available,utc=True,format="mixed")
    panel.to_parquet(stage/"economic_calendar.parquet",index=False)
    counts={}
    for tag,cut in [("historique","2025-12-31T21:00:00Z"),("decision",policy["decision_utc"])]:
        view=visible(panel,cut,["series","day"])
        view.to_parquet(stage/f"macro_{tag}.parquet",index=False)
        counts[tag]=view.series.value_counts().to_dict()
    return counts


def main():
    policy=json.loads(Path("config/catalogue-4.json").read_bytes())
    sources=json.loads(Path("config/sources-4.json").read_bytes())
    target=DEST/policy["version"]
    DEST.mkdir(parents=True,exist_ok=True)
    dependency_files=[Path(__file__).with_name(n) for n in ("build.py","sources.py","controls.py","statistics.py","equities.sql")]
    dependency_files.extend(Path(p) for p in ("config/catalogue-4.json","config/sources-4.json","config/import-2026-11-23.json",
                                               "config/references-1.4.json","reports/01-4-references/resultats.json"))
    fingerprint=sha256(b"".join(p.read_bytes() for p in dependency_files)).hexdigest()
    if target.exists():
        manifest=json.loads((target/"manifest.json").read_bytes())
        legacy_export = fingerprint != manifest["build"]
        if legacy_export:
            translation = json.loads(Path("config/catalogue-4-translation.json").read_bytes())
        if legacy_export and (manifest["build"], fingerprint) != (
            translation["original_build"], translation["english_build"]
        ):
            raise ValueError("Revised parameters or calculations: choose a new vintage.")
        for src in sources.values():
            checked(RAW/src["file"],src["sha256"])
        for src in json.loads(Path("config/import-2026-11-23.json").read_bytes())["sources"]:
            checked(Path("data/local/1.3/raw")/src["file"],src["sha256"])
        for filename,digest in manifest["products"].items():
            checked(target/filename,digest)
        if legacy_export:
            # Keep the English public report alongside the immutable source-language archive.
            checked(REPORT/"resultats.json", translation["english_report"])
        else:
            write_json(REPORT/"resultats.json",json.loads((target/"summary.json").read_bytes()))
        print("Verified catalogue snapshot:",target)
        return
    with TemporaryDirectory(dir=DEST) as tmp:
        stage=Path(tmp)/"catalogue"
        stage.mkdir()
        summary=assemble(stage,policy,sources)
        schema={p.stem:str(pq.read_schema(p).remove_metadata()) for p in sorted(stage.glob("*.parquet"))}
        write_json(stage/"schemas.json",schema)
        write_json(stage/"summary.json",summary)
        products={}
        for p in sorted(stage.iterdir()):
            if p.is_file():
                with p.open("rb") as f:
                    products[p.name]=file_digest(f,"sha256").hexdigest()
        write_json(stage/"manifest.json",dict(build=fingerprint,products=products))
        stage.rename(target)
    write_json(REPORT/"resultats.json",summary)
    print("Catalogue:",target,"· sheets",summary["stock_sheets"]+summary["fund_sheets"])


if __name__=="__main__":
    main()
