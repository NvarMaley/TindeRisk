"""Verified local chapter 09 adapters and batch readers."""
from datetime import date, datetime, timezone
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import duckdb
import numpy as np
from riskmatch.analytics.descriptive_report import selected_source
from riskmatch.analytics.forecast_batch import contiguous
from riskmatch.analytics.volatility import volatility_models, covariance_models, dcc_correlation, VERSION
from riskmatch.contracts import RiskReport, RunMetadata, Status


def annualization(source, frequency):
    return {"monthly":12,"weekly":52,"daily":365 if source in ("btc","eth") else 252}.get(frequency)


def asset_risk(root, source, instrument, start, end, currency, kind, as_of):
    if start>end or end>as_of or currency not in ("USD","CHF") or kind not in ("price_return","total_return"):
        raise ValueError("Invalid risk window")
    path,entry=selected_source(root,source,as_of)
    k=annualization(source,entry["frequency"])
    if not k:raise ValueError("Irregular intervals have no fixed annualization")
    column=kind+("_chf" if currency=="CHF" else "")
    with duckdb.connect() as db:
        rows=db.execute(f"""select start_date,end_date,{column} from read_parquet(?)
            where instrument=? and end_date between ? and ? order by end_date desc limit 2500""",
            [str(path),instrument,start,end]).fetchall()[::-1]
    valid=contiguous(rows)
    result=volatility_models([v for _,v in valid],[d for d,_ in valid],k)
    return result|{"source":source,"frequency":entry["frequency"],"kind":kind,"currency":currency,
                   "last":str(valid[-1][0])}


def matrix_risk(root, series, start, end, currency, kind, as_of):
    if not isinstance(series,list) or not 2<=len(series)<=8 or start>end or end>as_of or currency not in ("USD","CHF") or kind not in ("price_return","total_return"):
        raise ValueError("Invalid covariance request")
    intervals=[]; conventions=set()
    column=kind+("_chf" if currency=="CHF" else "")
    with duckdb.connect() as db:
        for s in series:
            path,entry=selected_source(root,s["source"],as_of)
            conventions.add((entry["frequency"],annualization(s["source"],entry["frequency"])))
            rows=db.execute(f"""select start_date,end_date,{column} from read_parquet(?)
              where instrument=? and end_date between ? and ? and {column} is not null
              order by end_date""",[str(path),s["instrument"],start,end]).fetchall()
            intervals.append({(a,b):v for a,b,v in rows if a is not None and np.isfinite(v)})
    if len(conventions)!=1 or next(iter(conventions))[1] is None:
        raise ValueError("Require identical regular frequency and annualization")
    if len({(s["source"],s["instrument"]) for s in series})!=len(series):
        raise ValueError("Duplicate series")
    f,k=next(iter(conventions)); common=sorted(set.intersection(*(set(i) for i in intervals)))
    # DCC and covariance use a continuous exact common sequence, no gaps.
    valid=contiguous([(a,b,0.) for a,b in common])
    allowed={d for d,_ in valid}
    common=[i for i in common if i[1] in allowed][-2500:]
    values=np.array([[i[d] for i in intervals] for d in common])
    output=covariance_models(values,k)
    try:
        dcc=dcc_correlation(values)
        dcc["dates"]=[str(d[1]) for d in common[-len(dcc["test_correlations"]):]]
        output["dcc"]=dcc
    except (ValueError,RuntimeError,ArithmeticError,ImportError) as e:output["dcc_unavailable"]=str(e)
    upstream=json.loads((Path(root)/"data/processed/returns/report.json").read_text())["return_id"]
    run=hashlib.sha256(repr((VERSION,upstream,series,start,end,currency,kind,as_of)).encode()).hexdigest()
    stamp=datetime.combine(as_of,datetime.min.time(),tzinfo=timezone.utc)
    selected=output["models"][output["selected_model"]]["covariance"]
    contract=RiskReport(meta=RunMetadata(as_of=stamp,run_id=run,model_version=VERSION,
        units=(("covariance","squared decimal returns per period"),),provenance=(upstream,),status=Status.EXPERIMENTAL),
        snapshot_id=upstream,instrument_ids=tuple(f"{s['source']}:{s['instrument']}" for s in series),
        covariance=tuple(tuple(row) for row in selected),frequency=f,currency=currency)
    envelope=asdict(contract);envelope["meta"]["as_of"]=stamp.isoformat()
    return output|{"frequency":f,"currency":currency,"kind":kind,"series":series,"last":str(common[-1][1]),
                   "risk_report":envelope}


def risk_batch_report(root, as_of):
    base=Path(root)/"data/processed/risk"
    try:
        report=json.loads((base/"report.json").read_text())
        upstream=json.loads((Path(root)/"data/processed/returns/report.json").read_text())
        if report["data_version"]!=upstream["return_id"] or report["version"]!=VERSION or date.fromisoformat(report["as_of"])>as_of:
            return {"status":"unavailable"}
        run=report["run_id"]
        if len(run)!=64 or any(c not in "0123456789abcdef" for c in run):return {"status":"unavailable"}
        for name,digest in report["files"].items():
            if "/" in name or "\\" in name or name.startswith("."):return {"status":"unavailable"}
            with (base/run/name).open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=digest:return {"status":"unavailable"}
        return report
    except (OSError,ValueError,TypeError,KeyError):return {"status":"unavailable"}


def risk_batch_asset(root, as_of, asset_id):
    if not isinstance(asset_id,str) or len(asset_id)>100:raise ValueError("Invalid asset")
    report=risk_batch_report(root,as_of)
    if report["status"]!="complete":return report
    path=Path(root)/"data/processed/risk"/report["run_id"]/"assets.jsonl"
    prefix='{"id":'+json.dumps(asset_id)+','
    with path.open() as stream:
        for line in stream:
            if line.startswith(prefix):return json.loads(line)
    return {"status":"unavailable"}
