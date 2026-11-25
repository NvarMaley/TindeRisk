"""Read only verified local factor artifacts."""
from datetime import date
from pathlib import Path
import hashlib,json
from riskmatch.analytics.factors import VERSION


def factor_report(root,as_of):
    base=Path(root)/"data/processed/factors"
    try:
        r=json.loads((base/"report.json").read_text())
        upstream=json.loads((Path(root)/"data/processed/returns/report.json").read_text())
        if r["version"]!=VERSION or r["data_version"]!=upstream["return_id"] or date.fromisoformat(r["as_of"])>as_of:
            return {"status":"unavailable"}
        run=r["run_id"]
        if len(run)!=64 or any(c not in "0123456789abcdef" for c in run):
            return {"status":"unavailable"}
        for name,digest in r["files"].items():
            if "/" in name or "\\" in name or name.startswith("."):return {"status":"unavailable"}
            with (base/run/name).open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=digest:return {"status":"unavailable"}
        return r
    except (OSError,ValueError,KeyError,TypeError):return {"status":"unavailable"}


def factor_asset(root,as_of,asset_id):
    if not isinstance(asset_id,str) or len(asset_id)>100:raise ValueError("Invalid asset")
    r=factor_report(root,as_of)
    if r.get("status")!="complete":return r
    path=Path(root)/"data/processed/factors"/r["run_id"]/"assets.jsonl"
    prefix='{"id":'+json.dumps(asset_id)+','
    with path.open() as stream:
        for line in stream:
            if line.startswith(prefix):return json.loads(line)
    return {"status":"unavailable"}
