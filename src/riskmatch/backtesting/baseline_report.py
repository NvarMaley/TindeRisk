"""Local historical benchmark comparison with immutable reference definitions."""
from datetime import date
from pathlib import Path
import hashlib
import json
from collections import defaultdict
import duckdb
import numpy as np
from riskmatch.analytics.descriptive_report import selected_source
from riskmatch.market_data.returns import returns_report
from riskmatch.backtesting.baselines import VERSION, simulate, metrics
from riskmatch.analytics.forecast_batch import batch_report

TICKERS=('SPY','SHY','IEF','BIL','TIP')
IDS=('84398','89470','89469','92027','89959')
BENCHMARKS={'cash_proxy':(0,0,0,1,0),'equal_weight':(.2,.2,.2,.2,.2),'sixty_forty':(.6,0,.4,0,0),'market_cap_proxy':(1,0,0,0,0)}
SHOCK=np.array([-.30,-.03,-.10,0.,-.10])
WINDOWS={'global_financial_crisis':(date(2008,1,1),date(2008,12,31)), 'covid_2020':(date(2020,2,1),date(2020,3,31)), 'rate_shock_2022':(date(2022,1,1),date(2022,12,31))}


def continuous_segments(intervals):
    segments=[]
    for i in intervals:
        if not segments or segments[-1][-1][1]!=i[0]:segments.append([])
        segments[-1].append(i)
    return segments


def historical_windows(returns,intervals):
    out={}
    for key,(start,end) in WINDOWS.items():
        taken=[i for i,(_,b) in enumerate(intervals) if start<=b<=end]
        expected=(end.year-start.year)*12+end.month-start.month+1
        if len(taken)==expected:
            out[key]={'cumulative':float(np.prod(1+np.asarray(returns)[taken])-1),'first':str(intervals[taken[0]][0]),'last':str(intervals[taken[-1]][1])}
    return out


def broad_reference(root,as_of,currency,cost,core_intervals,core_returns,core_rf,upstream):
    """Static Chapter 8 vector; retrospective cohort bias, not a PIT stock strategy."""
    manifest=batch_report(root,as_of)
    if manifest.get('status')!='complete' or not manifest.get('common_monthly',{}).get('count'):return {'status':'unavailable','reason':'Chapter 8 common vector unavailable'}
    file=Path(root)/'data/processed/forecasts'/manifest['run_id']/'common_monthly_total_return.json';v=json.loads(file.read_text());assets=v['assets'];groups=defaultdict(list)
    for a in assets:groups[a['source']].append(str(a['instrument']))
    maps={};column='total_return_chf' if currency=='CHF' else 'total_return';folder=Path(root)/'data/processed/returns'/upstream['return_id'];allowed={x['dataset'] for x in upstream['datasets'] if x.get('frequency')=='monthly' and x.get('total_returns')}
    with duckdb.connect() as db:
        for source,ids in groups.items():
            if source not in allowed:raise ValueError('Cohort source unavailable')
            rows=db.execute(f'SELECT instrument,start_date,end_date,{column} FROM read_parquet(?) WHERE instrument IN (SELECT unnest(?)) AND end_date<=? AND (availability_time IS NULL OR CAST(availability_time AS DATE)<=?)',[str(folder/f'{source}.parquet'),ids,as_of,as_of]).fetchall()
            for instrument,a,b,r in rows:
                if a is not None and b is not None and r is not None and np.isfinite(r) and r>=-1:maps.setdefault((source,str(instrument)),{})[(a,b)]=r
    series=[maps.get((a['source'],str(a['instrument'])),{}) for a in assets];common=set(core_intervals)
    for m in series:common.intersection_update(m)
    segments=continuous_segments(sorted(common))
    if not segments or len(segments[-1])<12:return {'status':'unavailable','assets':len(assets),'reason':'Insufficient exact common monthly history'}
    intervals=segments[-1];index={i:j for j,i in enumerate(core_intervals)};ix=[index[i] for i in intervals];x=np.array([[m[i] for m in series] for i in intervals]);rf=core_rf[ix];core=core_returns[ix];out=[]
    cases=[('cohort_equal_weight',x,np.ones(len(assets))/len(assets),f) for f in ('monthly','quarterly','buy_hold')]
    cases.extend((k,core,w,'monthly' if k=='sixty_forty' else 'buy_hold') for k,w in BENCHMARKS.items() if k!='equal_weight')
    for k,values,w,f in cases:
        gross=simulate(values,intervals,w,frequency=f);net=simulate(values,intervals,w,frequency=f,cost_bps=cost);out.append({'method':k,'frequency':f,'gross':metrics(gross['returns'],rf),'net':metrics(net['returns'],rf),'annual_one_way_turnover':net['annual_one_way_turnover'],'fees':net['total_fees'],'nav':[q['twr_index'] for q in net['ledger']]})
    return {'status':'experimental','assets':len(assets),'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'months':len(intervals),'variants':out,'dates':[str(i[1]) for i in intervals],'warning':'Fixed end-of-sample cohort, survivorship/selection bias; not a point-in-time universe backtest.'}


def baseline_report(root,data):
    as_of=date.fromisoformat(data['as_of']);currency=data.get('currency','USD');cost=data.get('cost_bps',10);start=date.fromisoformat(data.get('start','1900-01-01'))
    if as_of>date.today() or start>=as_of or currency not in ('USD','CHF') or isinstance(cost,bool) or not isinstance(cost,(int,float)) or not np.isfinite(cost) or not 0<=cost<=200:raise ValueError('Invalid baseline request')
    upstream=returns_report(root,as_of);path,_=selected_source(root,'etf_crsp_monthly',as_of);column='total_return_chf' if currency=='CHF' else 'total_return';maps=[]
    with duckdb.connect() as db:
        for instrument in IDS:
            rows=db.execute(f'SELECT start_date,end_date,{column} FROM read_parquet(?) WHERE instrument=? AND start_date>=? AND end_date<=? AND (availability_time IS NULL OR CAST(availability_time AS DATE)<=?) ORDER BY end_date',[str(path),instrument,start,as_of,as_of]).fetchall()
            maps.append({(a,b):v for a,b,v in rows if a is not None and b is not None and v is not None and np.isfinite(v) and v>=-1})
        common=sorted(set.intersection(*(set(m) for m in maps)));rf_map={}
        if currency=='USD':
            # Direct monthly factor RF: CPI joins can omit otherwise valid RF months.
            pitbase=Path(root)/'data/processed/pit';pit=json.loads((pitbase/'report.json').read_text())
            if pit['snapshot_id']!=upstream['snapshot_id']:raise ValueError('RF snapshot mismatch')
            rfpath=pitbase/pit['snapshot_id']/'fama_french.parquet';entry=next(v for v in pit['datasets'] if v['dataset']=='fama_french')
            with rfpath.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=entry['file_hash']:raise ValueError('RF file mismatch')
            reference_months={(d.year,d.month):v for d,v in db.execute("SELECT observation_date,value FROM read_parquet(?) WHERE instrument='RF' AND frequency='monthly' AND observation_date<=?",[str(rfpath),as_of]).fetchall() if v is not None and np.isfinite(v)}
            rf_map={i:reference_months[(i[1].year,i[1].month)] for i in common if (i[1].year,i[1].month) in reference_months}
            common=[i for i in common if i in rf_map]
    segments=continuous_segments(common)
    if not segments or len(segments[-1])<12:raise ValueError('Latest continuous window has fewer than 12 matched monthly returns')
    intervals=segments[-1];x=np.array([[m[i] for m in maps] for i in intervals]);rf=np.array([rf_map[i] for i in intervals]) if currency=='USD' else x[:,3];reference='Fama-French monthly USD RF' if currency=='USD' else 'BIL CHF unhedged cash proxy (not risk-free)'
    variants=[]
    for key,w in BENCHMARKS.items():
        for frequency in (('buy_hold',) if key in ('cash_proxy','market_cap_proxy') else ('monthly','quarterly','buy_hold')):
            gross=simulate(x,intervals,w,frequency=frequency);net=simulate(x,intervals,w,frequency=frequency,cost_bps=cost)
            gm=metrics(gross['returns'],rf);nm=metrics(net['returns'],rf)
            sensitivity={str(b):metrics(simulate(x,intervals,w,frequency=frequency,cost_bps=b)['returns'],rf)['cagr'] for b in sorted({0,5,10,25,float(cost)})}
            variants.append({'id':key+'_'+frequency,'method':key,'frequency':frequency,'target_weights':dict(zip(TICKERS,w)),'end_weights':dict(zip(TICKERS,net['final_weights'])),'gross':gm,'net':nm,'gross_final_nav':gross['final_nav'],'net_final_nav':net['final_nav'],'fees':net['total_fees'],'initial_fee':net['initial']['fees'],'total_traded_notional':net['total_traded_notional'],'annual_one_way_turnover':net['annual_one_way_turnover'],'stress_loss':float(-SHOCK@np.array(net['final_weights'])),'historical_stress':historical_windows(net['returns'],intervals),'cost_sensitivity_cagr':sensitivity,'initial':net['initial'],'ledger':net['ledger']})
    fingerprint=hashlib.sha256(json.dumps([VERSION,upstream['return_id'],str(as_of),str(start),currency,cost],sort_keys=True).encode()).hexdigest()
    try:broad=broad_reference(root,as_of,currency,cost,intervals,x,rf,upstream)
    except (OSError,ValueError,KeyError,duckdb.Error) as exc:broad={'status':'unavailable','reason':str(exc)}
    return {'version':VERSION,'run_id':fingerprint,'data_version':upstream['return_id'],'status':'experimental','approved':False,'as_of':str(as_of),'currency':currency,'reference':reference,'reference_is_cash_proxy':currency=='CHF','source':'etf_crsp_monthly','point_in_time_verified':False,'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'months':len(intervals),'common_months':len(common),'segments':[{'start':str(s[0][0]),'end':str(s[-1][1]),'months':len(s)} for s in segments],'cost_bps':cost,'capital':100.,'tickers':TICKERS,'shock':dict(zip(TICKERS,SHOCK.tolist())),'variants':variants,'broad_reference':broad,'warning':'Retrospective close-to-close accounting, hypothetical execution; publication timestamps unavailable. ETF expense effects embedded, no taxes/slippage beyond specified proportional fee. Restricted reference set, not portfolio recommendations.'}
