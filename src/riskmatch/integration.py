"""Reconciled, local paper simulation export. No order execution."""
import base64
import csv
import hashlib
import io
import json
import math
import zipfile

VERSION="integration-v1"


def _json(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()


def _csv(rows,fields):
    buffer=io.StringIO(newline="")
    writer=csv.DictWriter(buffer,fieldnames=fields,extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def export_simulation(report, policy):
    """Validate server-generated output and produce a self-contained ZIP in memory."""
    if report["status"]!="experimental" or policy not in report["policies"]:
        raise ValueError("Unknown or unavailable policy")
    result=report["policies"][policy]
    if result["status"]!="computed" or not result["ledger"]:
        raise ValueError("Incomplete simulation cannot be confirmed")
    rows=result["ledger"]
    labels=[*report["names"],"USD cash"]
    if [r["date"] for r in rows]!=report["dates"]:
        raise ValueError("Ledger dates mismatch")
    weights=[];positions=[];trades=[];audit=[]
    previous=report["settings"]["capital"]
    for row in rows:
        if not math.isclose(row["opening"],previous,abs_tol=1e-6) or not math.isclose(
            row["opening"]+row["flow"]-row["fee"]+row["pnl"],row["ending"],abs_tol=1e-6):
            raise ValueError("Unreconciled ledger")
        if row["fee"]<0 or row["stress_estimate"]>report["settings"]["stress_limit"]+1e-8:
            raise ValueError("Paper allocation violates constraints")
        if len(row["weights"])!=len(labels) or len(row["end_positions"])!=len(labels) or len(row["trade_deltas"])!=len(labels)-1:
            raise ValueError("Ledger dimension mismatch")
        if any(v < -1e-8 for v in row["weights"]+row["end_positions"]):
            raise ValueError("Unsupported negative exposure")
        if not math.isclose(sum(row["weights"]),1,abs_tol=1e-8) or not math.isclose(sum(row["end_positions"]),row["ending"],abs_tol=1e-6):
            raise ValueError("Invalid funded exposures")
        if row["opening"]+row["flow"]<=0 or not math.isclose(
            row["ending"]/(row["opening"]+row["flow"])-1,row["return_"],abs_tol=1e-10):
            raise ValueError("Return reconciliation failed")
        if "cost_bps" in report["settings"] and not math.isclose(
            sum(abs(v) for v in row["trade_deltas"])*report["settings"]["cost_bps"]/10000,row["fee"],abs_tol=1e-6):
            raise ValueError("Trade fee reconciliation failed")
        previous=row["ending"]
        for name,w,notional in zip(labels,row["weights"],row["end_positions"]):
            weights.append({"date":row["date"],"sleeve":name,"executed_weight":w})
            positions.append({"date":row["date"],"sleeve":name,"ending_notional_usd":notional})
        for name,delta in zip(labels,row["trade_deltas"]):
            if abs(delta)>1e-8:
                trades.append({"date":row["date"],"sleeve":name,"signed_notional_usd":delta})
        audit.append({"date":row["date"],"status":"reconciled","row_sha256":hashlib.sha256(_json(row)).hexdigest()})
    if not math.isclose(sum(r["fee"] for r in rows),result["fees"],abs_tol=1e-6):
        raise ValueError("Fee total mismatch")
    selection=report["selection"]
    assumptions={"version":VERSION,"dynamic_version":report["version"],"match_version":report["match_version"],
                 "reference_run":report["reference_run"],"policy":policy,"settings":report["settings"],
                 "assumptions":report["assumptions"],"paper_only":True,
                 "positions_unit":"USD sleeve account notionals; not individual security quantities",
                 "scenarios_scope":"Chapter 25 selected basket before dynamic cash overlay"}
    files={
        "weights.csv":_csv(weights,["date","sleeve","executed_weight"]),
        "positions.csv":_csv(positions,["date","sleeve","ending_notional_usd"]),
        "trades.csv":_csv(trades,["date","sleeve","signed_notional_usd"]),
        "nav.csv":_csv(rows,["date","opening","flow","fee","pnl","ending","return_","turnover"]),
        "metrics.json":_json({k:v for k,v in result.items() if k not in ("ledger","nav")}),
        "exposures.csv":_csv([{"asset":k,"weight":v} for k,v in selection["weights"].items()],["asset","weight"]),
        "scenarios.csv":_csv([{"scenario":k,"return":v} for k,v in selection["scenarios"].items()],["scenario","return"]),
        "assumptions.json":_json(assumptions),
        "audit.json":_json(audit),
        "ledger.json":_json(rows),
        "sensitivity.json":_json(report["sensitivity"]),
    }
    manifest={name:hashlib.sha256(content).hexdigest() for name,content in files.items()}
    run_id=hashlib.sha256(_json(manifest)).hexdigest()
    files["manifest.json"]=_json({"run_id":run_id,"files":manifest})
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in files.items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,content)
    return {"status":"reconciled","paper_only":True,"run_id":run_id,
            "filename":"RiskMatch-"+run_id[:12]+".zip",
            "archive":base64.b64encode(buffer.getvalue()).decode("ascii")}
