"""Check distinct catalogue coverage against verified chapter 6/7 artifacts."""
from collections import Counter
from datetime import date
import argparse
import json
from pathlib import Path
import sys

import duckdb

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from riskmatch.analytics.descriptive_report import client_catalog, descriptive_report
from riskmatch.market_data.point_in_time import snapshot_report
from riskmatch.market_data.returns import returns_report


def audit(as_of):
    catalogue=client_catalog(ROOT,as_of)["items"]
    pit=snapshot_report(ROOT,as_of)
    returns=returns_report(ROOT,as_of)
    stats=descriptive_report(ROOT,as_of)
    if not all(r.get("datasets") for r in (pit,returns,stats)):
        raise ValueError("Verified chapters 5–7 snapshots required")
    path=ROOT/"data/processed/descriptive"/stats["descriptive_id"]/"asset_statistics.parquet"
    with duckdb.connect() as db:
        valid=set(db.execute("""select distinct source,instrument from read_parquet(?)
            where cast(json_extract(statistics,'$.count') as integer)>0""",[str(path)]).fetchall())
    classes={}
    for asset in catalogue:
        c=classes.setdefault(asset["category"],Counter())
        c["catalogue"]+=1
        c["returns"]+=bool(asset["series"])
        c["statistics"]+=any((s["source"],s["instrument"]) in valid for s in asset["series"])
    return {"as_of":as_of.isoformat(),"totals":dict(sum(classes.values(),Counter())),
            "categories":{k:dict(v) for k,v in classes.items()},
            "partitions":{name:len(r["datasets"]) for name,r in (("pit",pit),("returns",returns),("descriptive",stats))},
            "approved":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of",type=date.fromisoformat,default=date.today())
    print(json.dumps(audit(parser.parse_args().as_of),indent=2))
