"""Aligned USD monthly cash reference; separate from frozen forecast artifacts."""
from datetime import date
from pathlib import Path
import hashlib
import json
import numpy as np
import duckdb


def benchmark(returns, dates, rf, window=20):
    """Strict prior-month forecast; contemporaneous RF is realized benchmark only."""
    y=np.asarray(returns,float);cash=np.asarray(rf,float)
    if y.shape!=cash.shape or y.ndim!=1 or len(y)!=len(dates) or len(y)<100 or not isinstance(window,int) or not 1<=window<=len(y)-5 or not np.isfinite(np.c_[y,cash]).all() or np.any(y< -1) or np.any(cash< -1):
        raise ValueError("Invalid aligned cash benchmark")
    if any(a>=b for a,b in zip(dates,dates[1:])):
        raise ValueError("Invalid dates")
    n=len(y)-window
    start=window+int(.8*n)
    actual=y[start:];prediction=cash[start-1:-1];realized=cash[start:]
    return {"status":"experimental","version":"cash-reference-v1","observations":len(y),
            "test_count":len(actual),"first":str(dates[start]),"last":str(dates[-1]),
            "lagged_cash_mse":float(np.mean((actual-prediction)**2)),
            "zero_return_mse":float(np.mean(actual**2)),
            "cash_mean":float(realized.mean()),"asset_mean":float(actual.mean()),
            "excess_mean":float((actual-realized).mean()),
            "cash_cumulative":float(np.prod(1+realized)-1),
            "asset_cumulative":float(np.prod(1+actual)-1),
            "history":[[str(d),float(a),float(p),float(c)] for d,a,p,c in zip(dates[start:],actual,prediction,realized)],
            "warning":"Historical RF archive; original release timestamps unverified. Lagged RF comparator is retrospective, not a certified executable forecast."}


def monthly_reference(root, returns, dates, as_of, data_version):
    base=Path(root)/"data/processed/pit"
    try:
        p=json.loads((base/"report.json").read_text())
        upstream=json.loads((Path(root)/"data/processed/returns/report.json").read_text())
        if upstream["return_id"]!=data_version or upstream["snapshot_id"]!=p["snapshot_id"]:
            raise ValueError("Snapshot mismatch")
        entry=next(row for row in p["datasets"] if row["dataset"]=="fama_french")
        path=base/p["snapshot_id"]/"fama_french.parquet"
        with path.open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest()!=entry["file_hash"]:
                raise ValueError("RF archive hash mismatch")
        with duckdb.connect() as db:
            rows=db.execute("select observation_date,value from read_parquet(?) where instrument='RF' and frequency='monthly' and observation_date<=?",[str(path),as_of]).fetchall()
        rf={(d.year,d.month):v for d,v in rows}
        if len(rf)!=len(rows):
            raise ValueError("Duplicate RF month")
        months=[(d.year,d.month) for d in dates]
        if len(set(months))!=len(months) or any(b[0]*12+b[1]-a[0]*12-a[1]!=1 for a,b in zip(months,months[1:])):
            raise ValueError("Noncontinuous monthly asset dates")
        values=[rf.get(m) for m in months]
        if any(v is None for v in values):
            raise ValueError("Incomplete RF coverage")
        return benchmark(returns,dates,values)|{"data_version":data_version,"source_hash":entry["file_hash"]}
    except (OSError,ValueError,KeyError,StopIteration,TypeError,duckdb.Error):
        return {"status":"unavailable","reason":"Verified continuous matching RF history unavailable"}
