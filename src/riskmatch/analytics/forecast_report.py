"""Local forecast adapter; return-source provenance and exact-interval checks."""
from pathlib import Path
import duckdb
from riskmatch.analytics.descriptive_report import selected_source
from riskmatch.analytics.forecasting import forecast


def asset_forecast(root, source, instrument, start, end, currency, kind, as_of,
                   include_ml=False):
    if not isinstance(instrument,str) or not instrument or len(instrument)>100:
        raise ValueError("Invalid asset")
    if start>end or end>as_of or currency not in ("USD","CHF") or kind not in ("total_return","price_return"):
        raise ValueError("Invalid forecast window")
    if not isinstance(include_ml,bool):
        raise ValueError("Invalid model selection")
    path, entry=selected_source(root,source,as_of)
    if entry["frequency"] not in ("daily","weekly","monthly"):
        raise ValueError("Forecasting requires regular daily, weekly or monthly returns")
    column=kind+("_chf" if currency=="CHF" else "")
    with duckdb.connect() as db:
        rows=db.execute(f"""select start_date,end_date,{column} from read_parquet(?)
            where instrument=? and end_date between ? and ? order by end_date desc limit 2500""",
            [str(path),instrument,start,end]).fetchall()[::-1]
    # Latest contiguous run only: do not silently compress missing observations.
    import math
    valid=[]
    for first,last,value in rows:
        if first is None or value is None or not math.isfinite(value):
            valid=[]
            continue
        if valid and first!=valid[-1][0]:
            valid=[]
        valid.append((last,value))
    result=forecast([v for _,v in valid],[d for d,_ in valid],instrument=instrument,
                    frequency=entry["frequency"],currency=currency,kind=kind,
                    data_version=Path(path).parent.name,as_of=as_of,include_ml=include_ml)
    if currency=="USD" and entry["frequency"]=="monthly" and kind=="total_return":
        from riskmatch.analytics.cash_reference import monthly_reference
        result["cash_reference"]=monthly_reference(root,[v for _,v in valid],[d for d,_ in valid],as_of,Path(path).parent.name)
    return result | {"observations":len(valid),"first":str(valid[0][0]),"last":str(valid[-1][0]),
                     "source":source,"instrument":instrument,"max_history":2500}
