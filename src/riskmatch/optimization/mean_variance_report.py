"""Matched Chapter 8/9/13 research data; prospective snapshot and disjoint holdout."""
from datetime import date
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import tempfile
import numpy as np
import duckdb
from sklearn.covariance import LedoitWolf
from threadpoolctl import threadpool_limits
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.analytics.descriptive_report import client_catalog
from riskmatch.market_data.returns import returns_report
from riskmatch.backtesting.baseline_report import IDS,TICKERS,continuous_segments
from riskmatch.backtesting.baselines import simulate,metrics
from riskmatch.profiling.mandate import validate_mandate
from riskmatch.optimization.mean_variance import MeanVariance,Constraints,VERSION


def aligned(root,as_of,currency,scope,*,instrument_categories=None):
    upstream=returns_report(root,as_of)
    if not upstream.get('return_id'):raise ValueError('matchingArchiveUnavailable')
    folder=Path(root)/'data/processed/returns'/upstream['return_id'];manifest=batch_report(root,as_of)
    if scope=='cohort':
        if manifest.get('status')!='complete' or not manifest.get('common_monthly',{}).get('count'):raise ValueError('Chapter 8 common vector unavailable')
        v=json.loads((Path(root)/'data/processed/forecasts'/manifest['run_id']/'common_monthly_total_return.json').read_text());assets=v['assets'];end=date.fromisoformat(v['as_of'])
    else:
        assets=[{'id':f'ETF-{t}','source':'etf_crsp_monthly','instrument':i,'ticker':t} for i,t in zip(IDS,TICKERS)];end=as_of
    catalogue=client_catalog(root,as_of)['items'];lookup={a['id']:a for a in catalogue};by_ticker={a['ticker']:a for a in catalogue if a['category']!='stock'}
    for a in assets:
        meta=lookup.get(a['id']) or by_ticker.get(a.get('ticker')) or {};a['ticker']=meta.get('ticker',a.get('ticker',a['id']));a['category']=meta.get('category','unknown');a['name']=meta.get('name',a['ticker'])
    if instrument_categories is not None:
        assets = [asset for asset in assets if asset['category'] in instrument_categories]
    groups=defaultdict(list)
    for a in assets:groups[a['source']].append(str(a['instrument']))
    if 'etf_crsp_monthly' not in groups or '92027' not in groups['etf_crsp_monthly']:groups['etf_crsp_monthly'].append('92027')
    allowed={x['dataset'] for x in upstream['datasets'] if x.get('frequency')=='monthly' and x.get('total_returns')};maps={};col='total_return_chf' if currency=='CHF' else 'total_return'
    with duckdb.connect() as db:
        for source,ids in groups.items():
            if source not in allowed:raise ValueError('Unavailable monthly source')
            rows=db.execute(f'SELECT instrument,start_date,end_date,{col} FROM read_parquet(?) WHERE instrument IN (SELECT unnest(?)) AND end_date<=? AND (availability_time IS NULL OR CAST(availability_time AS DATE)<=?)',[str(folder/f'{source}.parquet'),ids,end,as_of]).fetchall()
            for i,a,b,r in rows:
                if a is not None and b is not None and r is not None and np.isfinite(r) and r>=-1:maps.setdefault((source,str(i)),{})[(a,b)]=r
        series=[maps.get((a['source'],str(a['instrument'])),{}) for a in assets];cash=maps.get(('etf_crsp_monthly','92027'),{});common=set(cash)
        for m in series:common.intersection_update(m)
        if currency=='USD':
            base=Path(root)/'data/processed/pit';p=json.loads((base/'report.json').read_text());entry=next(z for z in p['datasets'] if z['dataset']=='fama_french');path=base/p['snapshot_id']/'fama_french.parquet'
            if p['snapshot_id']!=upstream['snapshot_id']:raise ValueError('RF snapshot mismatch')
            with path.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=entry['file_hash']:raise ValueError('RF file mismatch')
            monthly={(d.year,d.month):r for d,r in db.execute("SELECT observation_date,value FROM read_parquet(?) WHERE instrument='RF' AND frequency='monthly' AND observation_date<=?",[str(path),end]).fetchall() if r is not None and np.isfinite(r)};rf={i:monthly[(i[1].year,i[1].month)] for i in common if (i[1].year,i[1].month) in monthly};common.intersection_update(rf)
        else:rf=cash
    segments=continuous_segments(sorted(common))
    if not segments or len(segments[-1])<36:raise ValueError('Need 36 exact continuous matched monthly intervals')
    intervals=segments[-1];x=np.array([[m[i] for m in series] for i in intervals]);return assets,intervals,x,np.array([rf[i] for i in intervals]),upstream['return_id']


def category(a):
    c=a['category']
    if c in ('stock','equity_etf'):return 'equity'
    if c in ('treasury','treasury_etf'):return 'treasury'
    if c=='reit_etf':return 'reit'
    return c


def config(assets,cap,penalty,mandate=None,short=False,turnover=None,linear_limits=None):
    n=len(assets);lower=np.full(n,-cap if short else 0.);upper=np.full(n,cap);gross=1.5 if short else 1.;rows=[];unknown=[]
    if mandate:
        m=validate_mandate(mandate)
        if m['conflicts']:raise ValueError('Mandate has structural conflicts')
        c=mandate['constraints'];allowed=set(c['allowed_assets']);permissions=c['allow_short'] and c['allow_leverage']
        if short and not permissions:raise ValueError('Short/leverage not permitted by mandate')
        for i,a in enumerate(assets):
            if category(a) not in allowed:lower[i]=upper[i]=0.
        hard=lambda k:c[k]['mode']=='hard' and c[k]['value'] is not None
        if hard('max_asset_weight'):upper=np.minimum(upper,c['max_asset_weight']['value']);lower=np.maximum(lower,-c['max_asset_weight']['value'])
        if hard('gross_limit'):gross=min(gross,c['gross_limit']['value'])
        if gross<1 or (hard('net_min') and c['net_min']['value']>1) or (hard('net_max') and c['net_max']['value']<1):raise ValueError('Funded net/gross constraints infeasible')
        if hard('max_turnover'):unknown.append('max_turnover requires actual starting positions')
        for k in ('max_issuer_weight','max_sector_weight','min_liquidity','volatility','max_cost','stress_loss','loss_budget'):
            if hard(k):unknown.append(k+' not certified')
        if c['esg_exclusions'].strip():unknown.append('ESG look-through unavailable')
        if c['tax_assumption']=='after_tax_required':unknown.append('after-tax model unavailable')
        if c['fx_hedge'] in ('partial','full'):unknown.append('FX hedge not modeled')
    if linear_limits is not None:
        if not isinstance(linear_limits,list) or len(linear_limits)>12:raise ValueError('Invalid explicit research exposures')
        ids=[a['id'] for a in assets];seen=set()
        for item in linear_limits:
            name=item['name'];coeff=item.get('coefficients');members=item.get('members');lo=item['lower'];hi=item['upper']
            if not isinstance(name,str) or not 0<len(name)<=60 or name in seen or name in ('budget','gross','target_return','turnover','lower','upper'):raise ValueError('Invalid exposure name')
            if coeff is not None and members is None and set(coeff)==set(ids):a=np.array([coeff[i] for i in ids],float)
            elif coeff is None and isinstance(members,list) and set(members)<=set(ids):a=np.array([float(i in members) for i in ids])
            else:raise ValueError('Provide complete coefficients or explicit member IDs')
            if not isinstance(lo,(int,float)) or not isinstance(hi,(int,float)) or not np.isfinite([lo,hi]).all() or lo>hi or not np.isfinite(a).all():raise ValueError('Invalid exposure bounds')
            rows.append((name,a,float(lo),float(hi)));seen.add(name)
    return Constraints(lower,upper,gross,rows,np.ones(n)/n,turnover,penalty),unknown


def compact(r,assets):
    if 'weights' not in r:return r
    w=r['weights'];rc=r.get('risk_contributions');rows=[{'id':a['id'],'ticker':a['ticker'],'category':a['category'],'weight':float(w[i]),'marginal_risk':r['marginal_risk'][i] if r['marginal_risk'] is not None else None,'risk_contribution':rc[i] if rc is not None else None} for i,a in enumerate(assets)]
    return {k:v for k,v in r.items() if k not in ('weights','marginal_risk','risk_contributions')}|{'holdings':rows,'nonzero_count':sum(abs(z)>1e-6 for z in w),'top_weights':sorted(rows,key=lambda z:abs(z['weight']),reverse=True)[:15]}


def fit(x,mu,rf,c):
    lw=LedoitWolf().fit(x);model=MeanVariance(mu,lw.covariance_*12,rf,c)
    return model,float(lw.shrinkage_)


def regularized_mean(history,forecast=None):
    """Explicit research heuristic, not an empirically calibrated expected return."""
    h=np.asarray(history,float).mean(0)*12;anchor=float(np.median(h))
    if forecast is None:combined=h
    else:
        raw=np.asarray(forecast,float)*12;lo,hi=np.quantile(raw,[.05,.95]);combined=.5*h+.5*np.clip(raw,lo,hi)
    return .5*combined+.5*anchor


def class_regularized_mean(history, assets):
    """Annualized trailing means shrunk halfway toward their own asset class."""
    annual = np.asarray(history, dtype=float).mean(axis=0) * 12
    classes = np.array([category(asset) for asset in assets])
    for kind in np.unique(classes):
        group = classes == kind
        annual[group] = .5 * annual[group] + .5 * np.median(annual[group])
    return annual


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);currency=data.get('currency','USD');scope=data.get('scope','cohort');cap=data.get('max_weight',.05 if scope=='cohort' else .65);lam=data.get('risk_aversion',3.);penalty=data.get('turnover_penalty',.001);cost=data.get('cost_bps',10.);mandate=data.get('mandate');mean_model=data.get('mean_model','regularized')
    if as_of>date.today() or currency not in ('USD','CHF') or scope not in ('cohort','core') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in (cap,lam,penalty,cost)) or not 0<cap<=1 or not .01<=lam<=100 or not 0<=penalty<=.1 or not 0<=cost<=200:raise ValueError('Invalid mean-variance settings')
    if mandate is not None and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    if mean_model not in ('regularized','raw_forecast','historical'):raise ValueError('Invalid mean model')
    target=data.get('target_return');turnover=data.get('turnover_cap');linear=data.get('linear_limits')
    for v in (target,turnover):
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v)):raise ValueError('Invalid target or turnover cap')
    if turnover is not None and not 0<=turnover<=1:raise ValueError('Invalid research turnover cap')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,data_version=aligned(root,as_of,currency,scope);n=len(assets);c,unknown=config(assets,cap,penalty,mandate,turnover=turnover,linear_limits=linear)
        # Snapshot forecast vector is available only in USD cohort, same monthly horizon.
        prospective=scope=='cohort' and currency=='USD' and all(a.get('expected_return') is not None for a in assets)
        raw=np.array([a['expected_return'] for a in assets]) if prospective else None
        if mean_model=='raw_forecast' and raw is None:raise ValueError('Raw Chapter 8 vector only available for USD cohort')
        mu=regularized_mean(x,raw) if mean_model=='regularized' else raw*12 if mean_model=='raw_forecast' else x.mean(0)*12
        model,shrink=fit(x,mu,float(rf[-1]*12),c)
        if not model.feasible:return {'status':'infeasible','reason':model.feasibility.message,'assets':n,'unverified_mandate_constraints':unknown}
        minimum,frontier=model.frontier(points=9);sharpe=model.max_sharpe((minimum,frontier));utility=model.solve(return_weight=1.,variance_weight=lam,penalty=0.,warm=minimum.get('weights'));sensitivity=[model.solve(return_weight=1.,variance_weight=l,penalty=0.,warm=utility.get('weights'))|{'lambda':l} for l in (1.,3.,10.)]
        penalized=model.solve(return_weight=1.,variance_weight=lam,warm=utility.get('weights'));custom_target=model.solve(target=target,penalty=0.) if target is not None else None
        # Explicitly check an infeasible target above the feasible range.
        infeasible=model.solve(target=model.max_return+.01)
        # Chronological holdout: refit arithmetic mean and covariance on training only.
        cut=int(.8*len(x));train=x[:cut];test=x[cut:];dates=intervals[cut:];test_rf=rf[cut:];train_rf=float(rf[:cut].mean()*12);train_mu=regularized_mean(train) if mean_model=='regularized' else train.mean(0)*12;oc,_=config(assets,cap,penalty,mandate,turnover=turnover,linear_limits=linear);oos,_=fit(train,train_mu,train_rf,oc);oos_rows=[]
        def evaluate(label,row):
            if row.get('status')!='optimal':return {'id':label,'status':row.get('status'),'reason':row.get('reason',row.get('message'))}
            w=np.asarray(row['weights']);
            if np.min(w)<-1e-8:
                # Signed constant-mix reference; financing/borrow costs are unavailable. No claim of net executable performance.
                rr=test@w;return {'id':label,'status':'gross_only','metrics':metrics(rr,test_rf),'weights':w.tolist(),'warning':'Short borrow and financing not modeled'}
            w=np.maximum(w,0);w/=w.sum();net=simulate(test,dates,w,cost_bps=cost);gross=simulate(test,dates,w,cost_bps=0.);return {'id':label,'status':'computed','metrics':metrics(net['returns'],test_rf),'gross_metrics':metrics(gross['returns'],test_rf),'weights':w.tolist(),'nav':[q['twr_index'] for q in net['ledger']],'fees':net['total_fees'],'turnover':net['annual_one_way_turnover']}
        equal={'status':'optimal','weights':(np.ones(n)/n).tolist()};oos_rows.append(evaluate('equal_weight',equal))
        m0=oos.solve(penalty=0.);oos_rows.append(evaluate('minimum_variance',m0));oos_rows.append(evaluate('maximum_sharpe',oos.max_sharpe((m0,[]))));u=oos.solve(return_weight=1.,variance_weight=lam,penalty=0.,warm=m0.get('weights'));oos_rows.append(evaluate('maximum_utility',u));oos_rows.append(evaluate('turnover_penalized',oos.solve(return_weight=1.,variance_weight=lam,warm=u.get('weights'))))
        # Compare concentration and permitted shorting on same holdout. Small core signed variant only.
        tight=max(1/n,min(cap,cap/2));cc,_=config(assets,tight,0.,mandate,turnover=turnover,linear_limits=linear);cm,_=fit(train,train_mu,train_rf,cc);oos_rows.append(evaluate('tighter_cap',cm.solve(return_weight=1.,variance_weight=lam,penalty=0.)))
        if scope=='core' and (mandate is None or mandate['constraints']['allow_short'] and mandate['constraints']['allow_leverage']):
            sc,_=config(assets,cap,0.,mandate,short=True,turnover=turnover,linear_limits=linear);sm,_=fit(train,train_mu,train_rf,sc);oos_rows.append(evaluate('permitted_short_gross_only',sm.solve(return_weight=1.,variance_weight=lam,penalty=0.)))
        else:oos_rows.append({'id':'permitted_short_gross_only','status':'unavailable','reason':'Core signed comparison only; requires short and leverage permission when mandate applied'})
        models={'minimum_variance':compact(minimum,assets),'maximum_sharpe':compact(sharpe,assets),'maximum_utility':compact(utility,assets),'turnover_penalized':compact(penalized,assets)}
        if custom_target is not None:models['target_return']=compact(custom_target,assets)
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':data_version,'as_of':str(as_of),'currency':currency,'scope':scope,'asset_count':n,'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'observations':len(x),'mean_source':mean_model,'raw_forecast_available':prospective,'raw_forecast_annual_quantiles':np.quantile(raw*12,[0,.05,.5,.95,1]).tolist() if raw is not None else None,'effective_mean_annual_quantiles':np.quantile(mu,[0,.05,.5,.95,1]).tolist(),'covariance_source':'Ledoit-Wolf on exact matched returns, annualized','shrinkage':shrink,'min_eigenvalue':model.min_eigenvalue,'rf_annual':model.rf,'reference_is_cash_proxy':currency=='CHF','lambda':lam,'cap':cap,'gross_limit':c.gross,'turnover_penalty':penalty,'cost_bps':cost,'feasible_return_range':[model.min_return,model.max_return],'infeasible_target_test':infeasible['status'],'models':models,'frontier':[{'target':r.get('target'),'status':r['status'],'expected_return':r.get('expected_return'),'volatility':r.get('volatility'),'sharpe':r.get('sharpe'),'optimality_gap':r.get('optimality_gap')} for r in frontier],'lambda_sensitivity':[{'lambda':r['lambda'],'status':r['status'],'expected_return':r.get('expected_return'),'volatility':r.get('volatility'),'sharpe':r.get('sharpe')} for r in sensitivity],'holdout':{'train_months':cut,'test_months':len(test),'first':str(dates[0][0]),'last':str(dates[-1][1]),'dates':[str(b) for a,b in dates],'mean_source':'training_only_regularized_historical' if mean_model=='regularized' else 'training_only_historical','rows':[{k:v for k,v in row.items() if k!='weights'} for row in oos_rows]},'unverified_mandate_constraints':unknown,'configuration':{'scope':scope,'currency':currency,'max_weight':cap,'risk_aversion':lam,'turnover_penalty':penalty,'cost_bps':cost,'mean_model':mean_model,'target_return':target,'turnover_cap':turnover,'linear_limits':linear,'mandate_applied':mandate is not None},'warning':'Research only. Current static cohort selection is retrospective; holdout models refitted on training only, not PIT membership. No suitability, financing or executable price certification.'}


def cached_report(root,data):
    """Cache only public research configurations, never a client mandate."""
    if any(data.get(k) is not None for k in ('mandate','target_return','turnover_cap','linear_limits')):return run_report(root,data)
    root=Path(root);as_of=date.fromisoformat(data['as_of']);upstream=returns_report(root,as_of);forecast=batch_report(root,as_of)
    if not upstream.get('return_id'):raise ValueError('Return snapshot unavailable')
    scope=data.get('scope','cohort');settings={'as_of':str(as_of),'scope':scope,'currency':data.get('currency','USD'),'max_weight':data.get('max_weight',.05 if scope=='cohort' else .65),'risk_aversion':data.get('risk_aversion',3.),'turnover_penalty':data.get('turnover_penalty',.001),'cost_bps':data.get('cost_bps',10.),'mean_model':data.get('mean_model','regularized')}
    for k in ('max_weight','risk_aversion','turnover_penalty','cost_bps'):
        if isinstance(settings[k],bool) or not isinstance(settings[k],(int,float)) or not np.isfinite(settings[k]):raise ValueError('Invalid numeric configuration')
        settings[k]=float(settings[k])
    key=hashlib.sha256(json.dumps([VERSION,upstream['return_id'],forecast.get('run_id'),settings],sort_keys=True).encode()).hexdigest();base=root/'data/processed/mean_variance';path=base/f'{key}.json'
    try:
        result=json.loads(path.read_text())
        if result['run_id']==key and result['data_version']==upstream['return_id'] and result['version']==VERSION:return result
    except (OSError,ValueError,KeyError,TypeError):pass
    result=run_report(root,settings)|{'run_id':key,'configuration':settings}
    if result['status']=='experimental':
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(result,f,allow_nan=False);tmp=Path(f.name)
        tmp.replace(path)
    return result
