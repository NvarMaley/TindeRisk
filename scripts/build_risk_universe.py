"""Materialize chapter 09 research over the full catalogue, locally only."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import fcntl
for variable in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
    os.environ[variable]="1"
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import duckdb
import numpy as np
from riskmatch.analytics.descriptive_report import client_catalog, descriptive_report
from riskmatch.analytics.forecast_batch import prepare_item
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.analytics.risk_report import annualization
from riskmatch.analytics.volatility import volatility_models, covariance_models, dcc_correlation, VERSION
from riskmatch.market_data.returns import returns_report


def fit_asset(job):
    if job["status"]!="ready":return job
    clean={k:v for k,v in job.items() if k not in ("returns","dates","attempts")}
    try:
        risk=volatility_models(job["returns"],job["dates"],annualization(job["source"],job["frequency"]))
        return clean|{"status":"computed" if len(risk["models"])==6 and not any(
                      v.get("numerical_guard_count",0) for v in risk["models"].values()) else "partial",
                      "last":str(job["dates"][-1]),"risk":risk}
    except (ValueError,RuntimeError,ArithmeticError) as e:
        return clean|{"status":"error","reason":str(e)}


def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def build(as_of,workers):
    returns=returns_report(ROOT,as_of); desc=descriptive_report(ROOT,as_of)
    if not returns.get("datasets") or not desc.get("datasets"):raise ValueError("Missing verified chapters 6–7")
    catalogue=client_catalog(ROOT,as_of)["items"]; sources={r["dataset"] for r in returns["datasets"] if "total_returns" in r}
    folder=ROOT/"data/processed/returns"/returns["return_id"]
    stats=ROOT/"data/processed/descriptive"/desc["descriptive_id"]/"asset_statistics.parquet"
    base=ROOT/"data/processed/risk";base.mkdir(parents=True,exist_ok=True)
    run=hashlib.sha256(json.dumps([returns["return_id"],VERSION,as_of.isoformat(),[a["id"] for a in catalogue]]).encode()).hexdigest()
    dest=base/run;dest.mkdir(exist_ok=True)
    with (base/"build.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with duckdb.connect(config={"threads":1}) as db:
            descriptions={(s,i,k):(f,json.loads(v)) for s,i,k,f,v in db.execute(
                "select source,instrument,kind,frequency,statistics from read_parquet(?) where currency='USD'",[str(stats)]).fetchall()}
            jobs=[]
            for asset in catalogue:
                job=prepare_item(asset,db,folder,sources,as_of,minimum_observations=60)
                if job["status"]!="ready":
                    for kind in ("total_return","price_return"):
                        found=False
                        for s in asset["series"]:
                            item=descriptions.get((s["source"],s["instrument"],kind))
                            if item and item[1].get("volatility") is not None:
                                f,v=item;job|={"status":"descriptive_only","source":s["source"],"frequency":f,
                                    "kind":kind,"interval_volatility":v["volatility"],"observations":v["count"],
                                    "annualized_volatility":v.get("annualized_volatility") if f!="irregular" else None}
                                found=True;break
                        if found:break
                jobs.append(job)
        print(f"Catalogue {len(jobs)}; regular-model candidates {sum(j['status']=='ready' for j in jobs)}",flush=True)
        groups=defaultdict(list)
        for j in jobs:
            if j["status"]=="ready":
                groups[(j["frequency"],j["kind"],str(j["dates"][-1]),annualization(j["source"],j["frequency"]))].append(j)
        # Exact asset/source alignment with the Chapter 8 common-return vector.
        forecast_meta=batch_report(ROOT,as_of)
        if forecast_meta.get("status")=="complete" and forecast_meta.get("common_monthly",{}).get("count"):
            common_path=ROOT/"data/processed/forecasts"/forecast_meta["run_id"]/"common_monthly_total_return.json"
            vector=json.loads(common_path.read_text())
            identity={(a["id"],a["source"],a["instrument"]) for a in vector["assets"]}
            aligned=[j for j in jobs if j["status"]=="ready" and
                     (j["id"],j["source"],j["instrument"]) in identity and j["frequency"]=="monthly"
                     and j["kind"]=="total_return" and str(j["dates"][-1])==vector["as_of"]]
            if len(aligned)==len(identity):
                groups[("monthly","total_return",vector["as_of"],12,"chapter8_vector")]=aligned
        rows=[]
        path=dest/"assets.jsonl"
        with path.open("w") as stream, ProcessPoolExecutor(max_workers=workers) as pool:
            for row in pool.map(fit_asset,jobs,chunksize=4):
                rows.append(row);stream.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n");stream.flush()
                if len(rows)%100==0 or len(rows)==len(jobs):print(f"Risk profiles {len(rows)}/{len(jobs)}",flush=True)
        files={path.name:digest(path)}; cohorts=[]
        for index,(key,group) in enumerate(sorted(groups.items())):
            if len(group)<2:continue
            maps=[{(a,b):v for a,b,v in zip(j["dates"],j["dates"][1:],j["returns"][1:])} for j in group]
            common=sorted(set.intersection(*(set(m) for m in maps)))
            # Last common continuous interval chain only.
            chain=[]
            for interval in common:
                if chain and chain[-1][1]!=interval[0]:chain=[]
                chain.append(interval)
            if len(chain)<20:
                cohorts.append({"frequency":key[0],"kind":key[1],"last":key[2],"assets":len(group),"status":"insufficient_common_intervals","observations":len(chain)})
                continue
            values=np.array([[m[d] for m in maps] for d in chain])
            output=covariance_models(values,key[3]); summary={}
            arrays={}
            for model,v in output["models"].items():
                for name in ("covariance","annualized_covariance","regularized_covariance"):
                    arrays[f"{model}_{name}"]=np.asarray(v.pop(name))
                summary[model]=v
            filename=f"covariance-{index}.npz"
            np.savez_compressed(dest/filename,asset_ids=np.array([j["id"] for j in group]),**arrays)
            files[filename]=digest(dest/filename)
            row={"frequency":key[0],"kind":key[1],"last":key[2],"assets":len(group),"observations":len(chain),
                 "status":"computed","file":filename,"models":summary,
                 "cohort_type":key[4] if len(key)>4 else "regular",
                 "stability_reference":output["stability_reference"]}
            # DCC is restricted to small cohorts, not forced onto a large universe.
            if 2<=len(group)<=8 and len(chain)>=100:
                try:row["dcc"]=dcc_correlation(values)
                except (ValueError,RuntimeError,ArithmeticError,ImportError) as e:row["dcc_unavailable"]=str(e)
            cohorts.append(row)
        counts=Counter(r["status"] for r in rows);models=Counter(); categories=defaultdict(Counter)
        for row in rows:
            categories[row["category"]][row["status"]]+=1
            models.update(row.get("risk",{}).get("models",{}).keys())
        meta={"status":"complete","approved":False,"version":VERSION,"as_of":as_of.isoformat(),"run_id":run,
              "data_version":returns["return_id"],"catalogue_count":len(rows),"statuses":dict(counts),
              "by_category":{k:dict(v) for k,v in categories.items()},"by_model":dict(models),"cohorts":cohorts,"files":files}
        with tempfile.NamedTemporaryFile(mode="w",dir=base,delete=False) as stream:
            json.dump(meta,stream,allow_nan=False);tmp=Path(stream.name)
        tmp.replace(base/"report.json")
        print(json.dumps({"statuses":meta["statuses"],"models":meta["by_model"],"cohorts":len(cohorts)}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--as-of",type=date.fromisoformat,default=date.today())
    parser.add_argument("--workers",type=int,default=4,choices=range(1,9));args=parser.parse_args()
    build(args.as_of,args.workers)
