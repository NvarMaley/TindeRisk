"""Ingest pinned ETF prices, fund disclosures and local CRSP exports."""
import csv
from datetime import datetime
from hashlib import file_digest
import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xc
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .controls import align_sessions
from ..market_import import read_fx, read_prices

SECTORS = dict(XLB="Materials",XLE="Energy",XLF="Finance",XLI="Industrie",XLK="Technologie",
               XLP="Basic consumption",XLU="Community services",XLV="Health",XLY="Discretionary consumption")
S = pa.string()
F = pa.float64()
SCHEMAS = {
    "instruments": pa.schema([(k,S) for k in ("id","symbol","name","role","asset_class","issuer","exchange","currency",
                                "calendar","exposure","source","first_seen","last_seen","entry","exit","available")]),
    "prices":pa.schema([(k,S) for k in ("id","day","bar_timestamp","available","source")]
                       +[(k,F) for k in ("close","adjusted","volume","fx","return_usd","return_chf")]+[("session_close",S),("reason",S)]),
    "events":pa.schema([(k,S) for k in ("id","day","kind","source","available")]+[("cash",F),("split",F)]),
    "holdings":pa.schema([(k,S) for k in ("fund","day","available","security","issuer","currency","sector","source")]
                         +[("weight",F),("duration",F),("coupon",F),("maturity",S),("price",F)]),
    "fx":pa.schema([("day",S),("value",F),("unit",S),("source",S),("available",S)]),
    "sources":pa.schema([(k,S) for k in ("file","provider","url","retrieved","sha256","rights")])
}


def checked(path, digest):
    with path.open("rb") as stream:
        if file_digest(stream,"sha256").hexdigest()!=digest:
            raise ValueError(f"Modified checksum: {path.name}")


def save(frame, directory, key):
    schema=SCHEMAS.get(key)
    if schema:
        frame=frame.reindex(columns=schema.names)
    table=pa.Table.from_pandas(frame,schema=schema,preserve_index=False,safe=True)
    pq.write_table(table,directory/f"{key}.parquet",compression="zstd")


def source_tables(lock, raw, stage):
    sources=[]
    instruments=[]
    frames=[]
    calendar=xc.get_calendar("XNYS",start="2004-12-01",end="2027-01-01")
    events=[]
    fx_src=next(x for x in lock["sources"] if x["series"]=="DEXSZUS")
    fx_path=raw/fx_src["file"]
    checked(fx_path,fx_src["sha256"])
    fx=pd.Series(read_fx(fx_path.read_bytes()),dtype=float)
    fx.index=pd.to_datetime(fx.index)
    save(pd.DataFrame({"day":fx.index.strftime("%Y-%m-%d"),"value":fx.to_numpy(),"unit":"CHF/USD",
                       "source":"DEXSZUS","available":fx_src["retrieved_utc"]}),stage,"fx")
    for src in lock["sources"]:
        ticker=src["series"]
        sources.append(dict(file=src["file"],provider=src["provider"],url=src["url"],retrieved=src["retrieved_utc"],
                            sha256=src["sha256"],rights=lock["usage"]))
        if ticker=="DEXSZUS":
            continue
        path=raw/src["file"]
        checked(path,src["sha256"])
        buf=path.read_bytes()
        adjusted=read_prices(buf,ticker)
        chart=json.loads(json.loads(buf)["payload"])["chart"]["result"][0]
        meta=chart["meta"]
        q=chart["indicators"]["quote"][0]
        dates=pd.DatetimeIndex(adjusted)
        ident="ETF-"+str(meta["firstTradeDate"])+"-"+ticker
        d=pd.DataFrame(dict(id=ident,symbol=ticker,day=dates,adjusted=list(adjusted.values()),
                            close=q["close"],volume=q["volume"],source=src["file"],
                            available=src["retrieved_utc"],bar_timestamp=pd.to_datetime(chart["timestamp"],unit="s",utc=True).astype(str)))
        sessions=calendar.sessions_in_range(dates.min(),dates.max())
        d=align_sessions(d.set_index("day"),sessions,fx)
        d["id"],d["symbol"],d["source"],d["available"]=ident,ticker,src["file"],src["retrieved_utc"]
        d["session_close"]=calendar.schedule.loc[sessions,"close"].astype(str)
        d=d.rename_axis("day").reset_index()
        frames.append(d)
        for kind, values in chart.get("events",{}).items():
            for e in values.values():
                day=datetime.fromtimestamp(e["date"],ZoneInfo(meta["exchangeTimezoneName"])).date().isoformat()
                events.append(dict(id=ident,day=day,kind=kind,source=src["file"],available=src["retrieved_utc"],
                                   cash=e.get("amount"),split=e["numerator"]/e["denominator"] if kind=="splits" else None))
        cls="fonds_tresor" if ticker in ("IEF","TLT") else "vehicule_or" if ticker=="GLD" else "fonds_actions"
        instruments.append(dict(id=ident,symbol=ticker,name=meta["longName"],role="instrument",asset_class=cls,
                                issuer=meta["longName"],exchange=meta["fullExchangeName"],currency=meta["currency"],
                                calendar="US sessions observed",exposure="or" if ticker=="GLD" else "US",
                                source=src["file"],first_seen=str(dates.min().date()),last_seen=str(dates.max().date()),
                                entry=datetime.fromtimestamp(meta["firstTradeDate"],ZoneInfo(meta["exchangeTimezoneName"])).date().isoformat(),
                                available=src["retrieved_utc"]))
    prices=pd.concat(frames,ignore_index=True)
    save(prices.assign(day=prices.day.dt.strftime("%Y-%m-%d")),stage,"prices")
    save(pd.DataFrame(events),stage,"events")
    return instruments,prices,fx,sources


def issuer_code(value):
    """Issue identifier checksum, followed by its six-character issuing entity code."""
    s=str(value)
    if len(s)!=9 or not s.isalnum() or not s[-1].isdigit():
        return None
    vals = [int(ch,36)*(1+i%2) for i,ch in enumerate(s[:8])]
    if (sum(v//10+v%10 for v in vals)+int(s[-1]))%10:
        return None
    return "CUSIP6:"+s[:6]


def holdings_tables(sources, raw):
    frames=[]
    bonds=[]
    for filename,source in sources.items():
        if "-holdings." not in filename:
            continue
        ticker=filename.split("-")[0]
        path=raw/filename
        if path.suffix==".xlsx":
            x=pd.read_excel(path,header=None,dtype=str)
            if x.iat[1,1]!=ticker: raise ValueError("Identity of the incoherent fund")
            day=pd.to_datetime(x.iat[2,1],format="As of %d-%b-%Y").date().isoformat()
            x.columns=x.iloc[4];x=x.iloc[5:].copy()
            x["w"]=pd.to_numeric(x.Weight,errors="coerce")/100
            x=x[x.w.notna()].copy()
            x["security"]=x.Identifier
            equity=(x.Ticker.notna() & x.Ticker.ne("-") & ~x.Name.str.contains("DEC26|FUTURE",case=False,na=False))
            x["issuer"]=x.Identifier.map(issuer_code).where(equity)
            x["currency"]=x["Local Currency"]
            x["sector"]=SECTORS.get(ticker) if ticker in SECTORS else None
            x.loc[x.issuer.isna(),"sector"]=None
        else:
            text=path.read_text(encoding="utf-8-sig")
            header=next(line for line in text.splitlines() if line.startswith("Fund Holdings as of,"))
            day=pd.to_datetime(next(csv.reader([header]))[1],format="%b %d, %Y").date().isoformat()
            x=pd.read_csv(io.StringIO(text[text.index("Name,Sector,"):]),dtype=str)
            x["w"]=pd.to_numeric(x["Weight (%)"],errors="coerce")/100
            x=x[x.w.notna()].copy()
            x["security"]=x.CUSIP
            x["issuer"]=np.where(x.Sector.eq("Treasuries"),"US-TREASURY",None)
            x["currency"]=x["Market Currency"]
            x["sector"]=x.Sector
            for dest, col in [("duration","Duration"),("coupon","Coupon (%)"),("price","Price")]:
                x[dest]=pd.to_numeric(x[col],errors="coerce")
            x["maturity"]=pd.to_datetime(x.Maturity,format="%b %d, %Y",errors="coerce").dt.strftime("%Y-%m-%d")
            for _,r in x[x.issuer.eq("US-TREASURY") & x.ISIN.notna()].iterrows():
                bonds.append(dict(id="ISIN:"+r.ISIN,symbol=r.CUSIP,name=r.Name,role="instrument",
                                  asset_class="obligation_directe",issuer="US-TREASURY",exchange=None,currency="USD",
                                  calendar="US Treasury",exposure="US",source=filename,first_seen=day,last_seen=day,
                                  available=source["retrieved"]))
        if not .90 < x.w.sum() < 1.10: raise ValueError(f"Incoherent weights for {ticker}")
        frames.append(x.assign(fund=ticker,day=day,available=source["retrieved"],source=filename,weight=x.w)
                      .reindex(columns=SCHEMAS["holdings"].names))
    holdings=pd.concat(frames,ignore_index=True)
    return holdings,list({r["id"]:r for r in bonds}.values())


def crsp(stage, raw_file):
    con=duckdb.connect()
    con.execute("SET threads=3")
    con.execute("SET memory_limit='1GB'")
    con.execute("SET temp_directory=?", [str(stage/"duck-temp")])
    sql=Path(__file__).with_name("equities.sql").read_text()
    for i,statement in enumerate(con.extract_statements(sql)):
        con.execute(statement,{"raw_file":str(raw_file)} if i==0 else {})
    queries={
        "identifiers":"SELECT * FROM identifiers",
        "stock_months":"SELECT * EXCLUDE(variants) FROM months WHERE variants=1",
        "stock_quarantine":"""SELECT DISTINCT r.permno,r.day, CASE WHEN m.permno IS NULL THEN 'IDENTITE_HORS_DATE'
                               ELSE 'VERSIONS_EN_CONFLIT' END AS reason
                               FROM raw r LEFT JOIN months m USING(permno,day) WHERE m.permno IS NULL OR m.variants>1""",
        "stock_events":"""SELECT DISTINCT permno,ex_date,event_sequence,distribution_type,payment_type,payment_date,dividend,share_factor
                          FROM raw WHERE ex_date IS NOT NULL""",
    }
    for filename,query in queries.items():
        con.sql(query).write_parquet(str(stage/f"{filename}.parquet"),compression="zstd")
    return con
