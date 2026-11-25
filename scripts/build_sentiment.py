"""Build a strictly lagged local StockTwits experiment from safe Parquet only."""
import argparse,hashlib,json,sys,tempfile
from datetime import date
from pathlib import Path
from collections import defaultdict
import duckdb
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from riskmatch.analytics.sentiment import VERSION,compare_models,factor_returns,score
from riskmatch.analytics.descriptive_report import client_catalog
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.market_data.returns import returns_report
from riskmatch.market_data.local_sources import new_data_root


def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def build(as_of):
    new=new_data_root(ROOT)
    if new is None:raise ValueError('Local course archive unavailable')
    src=new/'data1/processed';file=src/'sentiment_firm_daily.parquet';metadata=json.loads((src/'sentiment_asset_metadata.json').read_text())
    if digest(file)!=metadata['source_sha256']:raise ValueError('Sentiment source hash mismatch')
    ret=returns_report(ROOT,as_of);folder=ROOT/'data/processed/returns'/ret['return_id'];pit=ROOT/'data/processed/pit';pmeta=json.loads((pit/'report.json').read_text());names=pit/pmeta['snapshot_id']/'wrds_names.parquet';ne=next(x for x in pmeta['datasets'] if x['dataset']=='wrds_names')
    if digest(names)!=ne['file_hash'] or pmeta['snapshot_id']!=ret['snapshot_id']:raise ValueError('Identity snapshot mismatch')
    catalog=client_catalog(ROOT,as_of)['items'];eligible=[]
    for a in catalog:
        s=next((s for s in a['series'] if s['source'] in ('stock_monthly','etf_crsp_monthly') and 'total_return' in s['kinds']),None)
        if s:eligible.append((a['id'],a['ticker'],s['source'],str(s['instrument'])))
    base=ROOT/'data/processed/sentiment';base.mkdir(parents=True,exist_ok=True);run=hashlib.sha256(repr((VERSION,ret['return_id'],metadata['source_sha256'],str(as_of))).encode()).hexdigest();dest=base/run;dest.mkdir(exist_ok=True)
    with duckdb.connect(config={'threads':4}) as db:
        db.execute('CREATE TEMP TABLE eligible(id VARCHAR,ticker VARCHAR,source VARCHAR,instrument VARCHAR)');db.executemany('INSERT INTO eligible VALUES (?,?,?,?)',eligible)
        db.execute("CREATE TEMP TABLE names AS SELECT upper(ticker) ticker,instrument,observation_date,valid_until_inclusive FROM read_parquet(?) WHERE ticker IS NOT NULL AND observation_date<=DATE '2020-03-23' AND valid_until_inclusive>=DATE '2009-07-10'",[str(names)])
        db.execute("""CREATE TEMP TABLE relevant AS SELECT DISTINCT ticker FROM names WHERE instrument IN (SELECT instrument FROM eligible)""")
        db.execute("""CREATE TEMP TABLE daily AS SELECT upper(ticker) ticker,CAST(timezone('UTC',date) AS DATE) d,Nbullish bull,Nbearish bear,N total FROM read_parquet(?) WHERE upper(ticker) IN (SELECT ticker FROM relevant) AND Nbullish>=0 AND Nbearish>=0 AND N>=Nbullish+Nbearish""",[str(file)])
        # Ticker reuse: accept only one historical permanent instrument across ALL active names.
        db.execute("""CREATE TEMP TABLE mapped AS SELECT d.ticker,d.d, min(n.instrument) instrument, d.bull,d.bear,d.total FROM daily d JOIN names n ON d.ticker=n.ticker AND d.d BETWEEN n.observation_date AND n.valid_until_inclusive GROUP BY d.ticker,d.d,d.bull,d.bear,d.total HAVING count(DISTINCT n.instrument)=1""")
        db.execute("""CREATE TEMP TABLE monthly AS SELECT instrument,CAST(date_trunc('month',d) AS DATE) AS sentiment_month,sum(bull) AS bull,sum(bear) AS bear,sum(total) AS total,count(*) AS observation_days FROM mapped WHERE d>=DATE '2009-08-01' AND d<DATE '2020-03-01' GROUP BY 1,2 HAVING sum(bull+bear)>=5 AND sum(total)>0""")
        db.execute("CREATE TEMP TABLE market AS SELECT 'stock_monthly' source,* FROM read_parquet(?) UNION ALL SELECT 'etf_crsp_monthly' source,* FROM read_parquet(?)",[str(folder/'stock_monthly.parquet'),str(folder/'etf_crsp_monthly.parquet')])
        # Lag one complete calendar month relative to period START, conservatively beyond next session.
        rows=db.execute("""WITH r AS (SELECT e.id,e.ticker,e.instrument,m.start_date,m.end_date,m.total_return,
          lag(m.total_return) OVER w prev_return,lag(m.end_date) OVER w prev_end,
          avg(m.total_return) OVER (PARTITION BY e.id ORDER BY m.end_date ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) trailing3,
          lag(m.end_date,3) OVER w third_end,
          avg(m.total_return) OVER (PARTITION BY e.id ORDER BY m.end_date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) historical_mean,
          sum(m.total_return*pow(1/.94,date_diff('month',DATE '1990-01-01',m.end_date))) OVER (PARTITION BY e.id ORDER BY m.end_date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)/nullif(sum(CASE WHEN m.total_return IS NOT NULL THEN pow(1/.94,date_diff('month',DATE '1990-01-01',m.end_date)) ELSE 0 END) OVER (PARTITION BY e.id ORDER BY m.end_date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) ewma_mean
          FROM market m JOIN eligible e USING(source,instrument)
          WHERE m.end_date<=? WINDOW w AS(PARTITION BY e.id ORDER BY m.end_date))
          SELECT r.id,r.ticker,r.start_date,r.end_date,r.total_return,r.prev_return,r.trailing3,m.sentiment_month,m.bull,m.bear,m.total,m.observation_days,
          (m.bull-m.bear)::DOUBLE/(m.bull+m.bear) polarity,(m.bull+m.bear)::DOUBLE/m.total labelled_share,ln(1+m.total) log_messages,r.historical_mean,r.ewma_mean
          FROM r JOIN monthly m ON r.instrument=m.instrument AND m.sentiment_month=CAST(date_trunc('month',r.start_date)-INTERVAL '1 month' AS DATE)
          WHERE r.total_return IS NOT NULL AND isfinite(r.total_return) AND r.prev_return IS NOT NULL AND isfinite(r.prev_return) AND r.trailing3 IS NOT NULL AND isfinite(r.trailing3) AND r.prev_end=r.start_date AND date_diff('month',r.third_end,r.end_date)=3 ORDER BY r.end_date,r.id""",[as_of]).fetchall()
        mapped_count=db.execute('SELECT count(*) FROM mapped').fetchone()[0];daily_count=db.execute('SELECT count(*) FROM daily').fetchone()[0]
    print('Aligned rows',len(rows),'assets',len({r[0] for r in rows}),flush=True)
    ids=np.array([r[0] for r in rows]);dates=np.array([str(r[3]) for r in rows]);y=np.array([r[4] for r in rows]);X=np.array([[r[5],r[6]] for r in rows]);S=np.array([[r[12],r[13],r[14]] for r in rows]);
    with threadpool_limits(limits=1):models,pred,test,split=compare_models(X,S,y,dates)
    refs={'historical':score(y[test],np.array([r[15] for r in rows])[test]),'rolling_3':score(y[test],X[test,1]),'ewma':score(y[test],np.array([r[16] for r in rows])[test])};factor=factor_returns(dates[test],ids[test],S[test,0],y[test]);factor_all=factor_returns(dates,ids,S[:,0],y);ic=[r['rank_ic'] for r in factor if r['rank_ic'] is not None]
    assets={};groups=defaultdict(list)
    for i,r in enumerate(rows):groups[r[0]].append(i)
    test_position={int(i):j for j,i in enumerate(np.flatnonzero(test))}
    for asset,ix in groups.items():
        j=np.asarray(ix);k=j[test[j]];series=[{'date':str(rows[i][7]),'return_end':str(rows[i][3]),'polarity':float(S[i,0]),'labelled_share':float(S[i,1]),'messages':int(rows[i][10])} for i in j]
        per_asset={}
        if len(k)>=5:
            pos=[test_position[int(i)] for i in k]
            for model in models:
                if (model,'baseline') in pred:per_asset[model]={'baseline':score(y[k],pred[(model,'baseline')][pos]),'sentiment':score(y[k],pred[(model,'sentiment')][pos])}
        assets[asset]={'id':asset,'ticker':rows[ix[-1]][1],'observations':len(ix),'first':series[0]['date'],'last':series[-1]['date'],'current_signal':None,'status':'historical_only','series':series,'test_count':len(k),'historical_model_comparison':per_asset}
    # Identical held-out dates and rows. Historical BL-style relative-view diagnostic:
    # compare ridge predicted top/bottom sentiment spread with its training historical mean prior;
    # fixed confidence 25% for illustration, not a production BL view.
    test_ix=np.flatnonzero(test);spread_baseline=factor_returns(dates[test],ids[test],S[test,0],pred[('ridge','baseline')]);spread_aug=factor_returns(dates[test],ids[test],S[test,0],pred[('ridge','sentiment')]);actual={r['date']:r['spread'] for r in factor};a={r['date']:r['spread'] for r in spread_baseline};b={r['date']:r['spread'] for r in spread_aug};common=sorted(set(actual)&set(a)&set(b));bl={}
    if common:
        actual_arr=np.array([actual[d] for d in common]);prior=np.array([a[d] for d in common]);view=np.array([b[d] for d in common]);bl={'months':len(common),'confidence':.25,'prior':score(actual_arr,prior),'view_posterior':score(actual_arr,.75*prior+.25*view),'note':'Scalar relative-view illustration; no current BL view enabled'}
    manifest=batch_report(ROOT,as_of);cohort=None
    if manifest.get('status')=='complete' and manifest.get('common_monthly',{}).get('count'):
        vector=json.loads((ROOT/'data/processed/forecasts'/manifest['run_id']/'common_monthly_total_return.json').read_text());cohort={'total':len(vector['assets']),'matched':sum(a['id'] in assets for a in vector['assets'])}
    path=dest/'assets.json';path.write_text(json.dumps(assets,allow_nan=False,separators=(',',':')))
    report={'version':VERSION,'status':'historical_only','approved':False,'as_of':str(as_of),'run_id':run,'return_id':ret['return_id'],'source_hash':metadata['source_sha256'],'asset_count':len(assets),'eligible_count':len(eligible),'aligned_rows':len(rows),'mapped_daily_rows':mapped_count,'eligible_tag_daily_rows':daily_count,'first':str(min(r[7] for r in rows)),'last':str(max(r[7] for r in rows)),'archive_last':'2020-03-23','current_signal_available':False,'split':split,'models':models,'reference_models':refs,'factor':{'all_months':len(factor_all),'test_months':len(factor),'mean_test_spread':float(np.mean([r['spread'] for r in factor])) if factor else None,'mean_test_rank_ic':float(np.mean(ic)) if ic else None,'test_series':factor},'black_litterman_diagnostic':bl,'file_hash':digest(path),'warning':'Retrospective course archive; historical identity mapping and conservative lag, no current sentiment or PIT certification. No recommendation or distribution.'}
    report['chapter8_cohort']=cohort
    with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(report,f,allow_nan=False);tmp=Path(f.name)
    tmp.replace(base/'report.json');print({k:report[k] for k in ('asset_count','eligible_count','aligned_rows','first','last','split')},flush=True);print({k:v.get('rmse_improvement') for k,v in models.items()},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of',type=date.fromisoformat,default=date.today());a=p.parse_args();build(a.as_of)
