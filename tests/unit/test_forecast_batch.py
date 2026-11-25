from datetime import date, timedelta
import hashlib
import json

import duckdb

from riskmatch.analytics.forecast_batch import prepare_item, contiguous, summarize_rows, batch_report, batch_asset
from riskmatch.analytics.forecasting import VERSION


def test_no_splicing_and_source_choice(tmp_path):
    day=date(2020,1,1)
    assert contiguous([(day,day+timedelta(days=1),.01),
                       (day+timedelta(days=3),day+timedelta(days=4),.02)]) == [(day+timedelta(days=4),.02)]
    item={"id":"asset","ticker":"A","category":"stock","series":[
        {"source":"short","instrument":"A","frequency":"monthly","kinds":["total_return"],"last":"2020-04-10"},
        {"source":"long","instrument":"A","frequency":"daily","kinds":["total_return"],"last":"2020-04-10"}]}
    with duckdb.connect() as db:
        for source,n in (("short",50),("long",110)):
            db.execute("""copy (select 'A' instrument,date '2020-01-01'+cast(i as int) start_date,
                date '2020-01-02'+cast(i as int) end_date,.01 total_return
                from range(?) t(i)) to ? (format parquet)""",[n,str(tmp_path/f"{source}.parquet")])
        row=prepare_item(item,db,tmp_path,{"short","long"},date(2021,1,1))
    assert row["source"]=="long" and len(row["returns"])==110
    assert row["attempts"][0]["observations"]==50
    assert summarize_rows([{"category":"stock","status":"unavailable","reason":"no_series"}])["statuses"]=={"unavailable":1}


def test_saved_batch_integrity(tmp_path):
    base=tmp_path/"data/processed"
    (base/"returns").mkdir(parents=True)
    (base/"returns/report.json").write_text(json.dumps({"return_id":"fixture"}))
    run_id="a"*64
    folder=base/"forecasts"/run_id
    folder.mkdir(parents=True)
    result=folder/"results.jsonl"
    row={"id":"A","status":"unavailable","reason":"no_series"}
    result.write_text(json.dumps(row,separators=(",",":"))+"\n")
    digest=hashlib.sha256(result.read_bytes()).hexdigest()
    (base/"forecasts/report.json").write_text(json.dumps({"status":"complete","run_id":run_id,
        "as_of":"2020-01-01","model_version":VERSION,"data_version":"fixture","file_hash":digest}))
    assert batch_report(tmp_path,date(2020,1,1))["status"]=="complete"
    assert batch_asset(tmp_path,date(2020,1,1),"A")==row
    assert batch_asset(tmp_path,date(2020,1,1),"absent")["reason"]=="asset_not_in_run"
    result.write_text("tampered")
    assert batch_report(tmp_path,date(2020,1,1))["status"]=="unavailable"
