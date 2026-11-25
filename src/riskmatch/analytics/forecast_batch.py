"""Local universe-wide research run; one auditable outcome per catalogue item."""
from collections import Counter
from datetime import date
from math import isfinite
from pathlib import Path
import hashlib
import json

from riskmatch.analytics.forecasting import forecast, MIN_OBSERVATIONS, VERSION

FREQUENCIES = ("monthly", "weekly", "daily")
CORE_MODELS = {"historical", "rolling", "ewma", "ols", "ridge", "lasso",
               "elastic_net", "random_forest", "xgboost", "neural_network"}


def contiguous(rows):
    """Extract the most recent valid contiguous run, preserving exact intervals."""
    valid=[]
    for first,last,value in rows:
        if first is None or last is None or value is None or not isfinite(value):
            valid=[]
            continue
        if valid and first!=valid[-1][0]:
            valid=[]
        valid.append((last,value))
    return valid


def prepare_item(item, db, folder, sources, as_of, minimum_observations=MIN_OBSERVATIONS):
    """Prefer total returns, then monthly, weekly, daily; never splice sources."""
    ident={k:item[k] for k in ("id","ticker","category")}
    candidates=item["series"]
    attempts=[]
    for kind in ("total_return","price_return"):
        for frequency in FREQUENCIES:
            selected=sorted((s for s in candidates if s["frequency"]==frequency and kind in s["kinds"]),
                            key=lambda s:(s["last"],s["source"]),reverse=True)
            for series in selected:
                source=series["source"]
                if source not in sources:
                    continue
                rows=db.execute(f"""select start_date,end_date,{kind} from read_parquet(?)
                    where instrument=? and end_date<=? order by end_date desc limit 2500""",
                    [str(folder/f"{source}.parquet"),series["instrument"],as_of]).fetchall()[::-1]
                valid=contiguous(rows)
                attempts.append({"source":source,"frequency":frequency,"kind":kind,"observations":len(valid)})
                if len(valid)>=minimum_observations:
                    return ident | {"status":"ready","source":source,"instrument":series["instrument"],
                        "frequency":frequency,"kind":kind,"currency":"USD","attempts":attempts,
                        "dates":[d for d,_ in valid],"returns":[v for _,v in valid]}
    reason=("no_series" if not candidates else "irregular_frequency" if not any(s["frequency"] in FREQUENCIES for s in candidates)
            else "insufficient_contiguous_history")
    return ident | {"status":"unavailable","reason":reason,"attempts":attempts}


def run_item(job):
    item,as_of,data_version=job
    if item["status"]!="ready":
        return item
    dates=item.pop("dates")
    returns=item.pop("returns")
    try:
        result=forecast(returns,dates,instrument=item["instrument"],frequency=item["frequency"],
                        currency=item["currency"],kind=item["kind"],data_version=data_version,
                        as_of=as_of,include_ml=True)
        missing=sorted(CORE_MODELS-result["models"].keys())
        return item | {"status":"partial" if missing else "computed","missing_models":missing,
                       "observations":len(dates),"first":str(dates[0]),"last":str(dates[-1]),"forecast":result}
    except Exception as exc:
        return item | {"status":"error","reason":type(exc).__name__,
                       "observations":len(dates),"first":str(dates[0]),"last":str(dates[-1])}


def summarize_rows(rows):
    states=Counter(r["status"] for r in rows)
    reasons=Counter(r["reason"] for r in rows if "reason" in r and r["status"] in ("unavailable","error"))
    fallback_reasons=Counter(r["reason"] for r in rows if "reason" in r and r["status"]=="fallback")
    categories={}
    groups=Counter()
    models=Counter()
    for row in rows:
        category=categories.setdefault(row["category"],Counter())
        category[row["status"]]+=1
        if "forecast" in row:
            groups[(row["frequency"],row["kind"],row["last"])]+=1
            models.update(row["forecast"]["models"].keys())
    return {"catalogue_count":len(rows),"statuses":dict(states),"reasons":dict(reasons),"fallback_reasons":dict(fallback_reasons),
            "by_category":{k:dict(v) for k,v in categories.items()},
            "by_model":dict(models),
            "cohorts":[{"frequency":f,"kind":k,"last":d,"count":n} for (f,k,d),n in sorted(groups.items())]}


def batch_report(root, as_of):
    """Read only a complete, verified, current local run; no licensed rows returned."""
    base=Path(root)/"data/processed/forecasts"
    try:
        meta=json.loads((base/"report.json").read_text())
        upstream=json.loads((Path(root)/"data/processed/returns/report.json").read_text())
        if meta["data_version"]!=upstream["return_id"] or meta["model_version"]!=VERSION or date.fromisoformat(meta["as_of"])>as_of:
            return {"status":"unavailable"}
        name=meta["run_id"]
        if len(name)!=64 or any(c not in "0123456789abcdef" for c in name):
            return {"status":"unavailable"}
        with (base/name/"results.jsonl").open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest()!=meta["file_hash"]:
                return {"status":"unavailable"}
        if "common_monthly" in meta:
            with (base/name/"common_monthly_total_return.json").open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=meta["common_monthly"]["file_hash"]:
                    return {"status":"unavailable"}
        return meta
    except (OSError,ValueError,TypeError,KeyError):
        return {"status":"unavailable"}


def batch_asset(root, as_of, asset_id):
    if not isinstance(asset_id,str) or not asset_id or len(asset_id)>100:
        raise ValueError("Invalid catalogue asset")
    meta=batch_report(root,as_of)
    if meta["status"]!="complete":
        return meta
    path=Path(root)/"data/processed/forecasts"/meta["run_id"]/"results.jsonl"
    prefix='{"id":'+json.dumps(asset_id)+','
    with path.open() as stream:
        for line in stream:
            if line.startswith(prefix):
                row=json.loads(line)
                if row["id"]==asset_id:
                    return row
    return {"status":"unavailable","reason":"asset_not_in_run"}
