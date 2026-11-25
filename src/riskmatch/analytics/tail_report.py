"""Verified local tail-risk artifacts and exact-interval comparison."""
import hashlib
import json
from datetime import date
from pathlib import Path
import duckdb
import numpy as np
from riskmatch.analytics.tail_risk import VERSION, dependence
from riskmatch.analytics.descriptive_report import selected_source
from riskmatch.analytics.forecast_batch import contiguous
from riskmatch.analytics.risk_report import annualization


def tail_report(root,as_of):
    base=Path(root)/'data/processed/tail'
    try:
        m=json.loads((base/'report.json').read_text()); upstream=json.loads((Path(root)/'data/processed/returns/report.json').read_text())
        run=m['run_id']
        if m['version']!=VERSION or m['data_version']!=upstream['return_id'] or date.fromisoformat(m['as_of'])>as_of or len(run)!=64 or any(c not in '0123456789abcdef' for c in run):return {'status':'unavailable'}
        with (base/run/'assets.jsonl').open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=m['files']['assets.jsonl']:return {'status':'unavailable'}
        return m
    except (OSError,KeyError,ValueError,TypeError):return {'status':'unavailable'}


def tail_asset(root,as_of,asset_id):
    if not isinstance(asset_id,str) or len(asset_id)>100:raise ValueError('Invalid asset')
    m=tail_report(root,as_of)
    if m['status']!='complete':return m
    with (Path(root)/'data/processed/tail'/m['run_id']/'assets.jsonl').open() as f:
        for line in f:
            if line.startswith('{"id":'+json.dumps(asset_id)+','):return json.loads(line)
    return {'status':'unavailable'}


def tail_matrix(root,as_of,data):
    series=data['series'];start=date.fromisoformat(data['start']);end=date.fromisoformat(data['end']);kind=data['kind'];currency=data['currency']
    if not 2<=len(series)<=8 or start>end or end>as_of or kind not in ('price_return','total_return') or currency not in ('USD','CHF'):raise ValueError('Invalid comparison')
    if len({(s['source'],s['instrument']) for s in series})!=len(series):raise ValueError('Duplicate series')
    col=kind+('_chf' if currency=='CHF' else '');maps=[]; conventions=set()
    with duckdb.connect() as db:
        for s in series:
            path,e=selected_source(root,s['source'],as_of);conventions.add((e['frequency'],annualization(s['source'],e['frequency'])))
            rows=db.execute(f'SELECT start_date,end_date,{col} FROM read_parquet(?) WHERE instrument=? AND end_date BETWEEN ? AND ? ORDER BY end_date',[str(path),s['instrument'],start,end]).fetchall()
            maps.append({(a,b):v for a,b,v in rows if a is not None and b is not None and v is not None and np.isfinite(v)})
    if len(conventions)!=1 or next(iter(conventions))[1] is None:raise ValueError('Incompatible intervals')
    common=sorted(set.intersection(*(set(m) for m in maps)));valid=contiguous([(a,b,0.) for a,b in common]);ends={d for d,_ in valid};common=[i for i in common if i[1] in ends][-2500:]
    return dependence([[m[i] for m in maps] for i in common])|{'frequency':next(iter(conventions))[0],'currency':currency,'kind':kind,'series':series,'last':str(common[-1][1])}
