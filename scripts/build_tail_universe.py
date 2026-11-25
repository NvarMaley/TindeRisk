"""Local-only catalogue tail risk build."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import duckdb
from riskmatch.analytics.descriptive_report import client_catalog
from riskmatch.analytics.forecast_batch import prepare_item, contiguous
from riskmatch.analytics.tail_risk import VERSION, profile
from riskmatch.market_data.returns import returns_report


def fit(job):
    if job['status']!='ready':return job
    dates=job.pop('dates'); returns=job.pop('returns');job.pop('attempts',None)
    try:
        result=profile(returns,dates,job['frequency']!='irregular')
        return job|{'status':'computed' if result['models'].get('95') else 'descriptive_only','last':str(dates[-1]),'tail':result}
    except (ValueError,ArithmeticError,RuntimeError) as e:return job|{'status':'error','reason':str(e)}


def build(as_of,workers):
    report=returns_report(ROOT,as_of);catalogue=client_catalog(ROOT,as_of)['items']
    sources={r['dataset'] for r in report['datasets'] if 'total_returns' in r}
    folder=ROOT/'data/processed/returns'/report['return_id'];jobs=[]
    with duckdb.connect(config={'threads':1}) as db:
        for asset in catalogue:
            job=prepare_item(asset,db,folder,sources,as_of,minimum_observations=500)
            if job['status']!='ready':job=prepare_item(asset,db,folder,sources,as_of,minimum_observations=100)
            if job['status']!='ready':job=prepare_item(asset,db,folder,sources,as_of,minimum_observations=2)
            if job['status']!='ready':
                for s in asset['series']:
                    if s['source'] not in sources:continue
                    kind='total_return' if 'total_return' in s['kinds'] else 'price_return'
                    rows=db.execute(f'SELECT start_date,end_date,{kind} FROM read_parquet(?) WHERE instrument=? AND end_date<=? ORDER BY end_date DESC LIMIT 2500',[str(folder/f"{s['source']}.parquet"),s['instrument'],as_of]).fetchall()[::-1]
                    valid=contiguous(rows)
                    if len(valid)>=2:
                        job|={'status':'ready','source':s['source'],'instrument':s['instrument'],'frequency':s['frequency'],'kind':kind,'currency':'USD','dates':[d for d,v in valid],'returns':[v for d,v in valid]};break
            jobs.append(job)
    base=ROOT/'data/processed/tail';base.mkdir(parents=True,exist_ok=True)
    run=hashlib.sha256(repr((VERSION,report['return_id'],as_of,[a['id'] for a in catalogue])).encode()).hexdigest()
    dest=base/run;dest.mkdir(exist_ok=True);path=dest/'assets.jsonl';counts=Counter();models=Counter()
    print('Prepared',len(jobs),flush=True)
    with path.open('w') as stream, ProcessPoolExecutor(max_workers=workers) as pool:
        for i,row in enumerate(pool.map(fit,jobs,chunksize=4),1):
            stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');counts[row['status']]+=1
            for level,items in row.get('tail',{}).get('models',{}).items():models.update(f'{level}_{k}' for k in items)
            if i%100==0:print(i,dict(counts),flush=True)
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    meta={'status':'complete','approved':False,'version':VERSION,'as_of':str(as_of),'run_id':run,'data_version':report['return_id'],'catalogue_count':len(jobs),'statuses':dict(counts),'by_model':dict(models),'files':{path.name:digest}}
    with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(meta,f);tmp=Path(f.name)
    tmp.replace(base/'report.json');print(meta,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of',type=date.fromisoformat,default=date.today());p.add_argument('--workers',type=int,default=4);a=p.parse_args();build(a.as_of,a.workers)
