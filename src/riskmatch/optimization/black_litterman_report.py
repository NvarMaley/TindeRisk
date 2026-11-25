"""Dated equity anchor, aggregate forecast views and independent optimizer."""
from datetime import date
from pathlib import Path
import hashlib
import json
import tempfile
import duckdb
import numpy as np
from sklearn.covariance import LedoitWolf
from threadpoolctl import threadpool_limits
from riskmatch.optimization.black_litterman import VERSION,posterior,delta_estimate
from riskmatch.optimization.mean_variance import MeanVariance
from riskmatch.optimization.mean_variance_report import aligned,config,compact,regularized_mean,category
from riskmatch.backtesting.baselines import simulate,metrics
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report


def market_anchor(root,assets,when,scope,anchor):
    n=len(assets)
    if anchor=='equal_weight':return np.ones(n)/n,{'source':'declared_equal_weight_reference','covered':n,'date':str(when)}
    if scope=='core':
        w=np.array([float(a['ticker']=='SPY') for a in assets]);return w,{'source':'SPY_US_large_cap_proxy_not_global_market','covered':1,'date':str(when)}
    base=Path(root)/'data/processed/pit';meta=json.loads((base/'report.json').read_text());entry=next(x for x in meta['datasets'] if x['dataset']=='stock_membership');path=base/meta['snapshot_id']/'stock_membership.parquet'
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=entry['file_hash']:raise ValueError('Market cap snapshot integrity failed')
    stock=[a['instrument'] for a in assets if a['source']=='stock_monthly'];
    with duckdb.connect() as db:
        rows=db.execute('SELECT instrument,market_cap_source_units FROM read_parquet(?) WHERE observation_date=? AND instrument IN (SELECT unnest(?)) AND market_cap_source_units>0',[str(path),when,stock]).fetchall()
    caps=dict(rows);w=np.array([caps.get(a['instrument'],0.) if a['source']=='stock_monthly' else 0. for a in assets]);covered=int((w>0).sum())
    if w.sum()<=0 or covered<.5*len(stock):raise ValueError('Insufficient dated market-cap coverage')
    return w/w.sum(),{'source':'dated_CRSP_subset_stock_market_cap_excludes_ETFs_to_avoid_double_counting','covered':covered,'eligible_stocks':len(stock),'date':str(when),'missing_stock_count':len(stock)-covered}


def default_views(assets,anchor,expected,rf):
    stock=np.array([float(category(a)=='equity') for a in assets]);bond=np.array([float(category(a)=='treasury') for a in assets]);rows=[];q=[];confidence=[];labels=[]
    equity=anchor*stock
    if equity.sum()==0:equity=stock
    if equity.sum()>0:
        equity=equity/equity.sum();rows.append(equity);q.append(float(equity@expected-rf));confidence.append(.35);labels.append('equity_basket_absolute')
    if bond.sum()>0:
        bond/=bond.sum();rows.append(bond);q.append(float(bond@expected-rf));confidence.append(.35);labels.append('treasury_basket_absolute')
        if equity.sum()>0:rows.append(equity-bond);q.append(float((equity-bond)@expected));confidence.append(.25);labels.append('equity_minus_treasury_relative')
    # These two absolute views and relative view share evidence; non-independent errors.
    corr=np.eye(len(rows))
    if len(rows)==3:corr=np.array([[1,0,.5],[0,1,-.5],[.5,-.5,1.]])
    return np.asarray(rows),np.asarray(q),np.asarray(confidence),corr,labels


def manual_views(assets,views,rf):
    if not isinstance(views,list) or len(views)>12:raise ValueError('At most 12 views')
    ids={a['id']:i for i,a in enumerate(assets)};P=[];q=[];conf=[];labels=[]
    for v in views:
        typ=v['type'];a=v['asset'];b=v.get('relative_to');target=v['return'];c=v['confidence']
        if a not in ids or typ not in ('absolute','relative') or any(isinstance(z,bool) or not isinstance(z,(int,float)) or not np.isfinite(z) for z in (target,c)) or not -1<=target<=2 or not 0<=c<=1:raise ValueError('Invalid manual view')
        row=np.zeros(len(assets));row[ids[a]]=1
        if typ=='relative':
            if b not in ids or b==a:raise ValueError('Relative view requires two different assets')
            row[ids[b]]=-1
        P.append(row);q.append(target-rf if typ=='absolute' else target);conf.append(c);labels.append(a if typ=='absolute' else a+' minus '+b)
    return np.asarray(P).reshape(-1,len(assets)),np.asarray(q),np.asarray(conf),np.eye(len(P)),labels


def compare_models(train,test,rf_train,rf_test,anchor,cov,delta,tau,assets,cap,lam,cost,dates,mandate):
    rf=float(rf_train.mean()*12);historic=train.mean(0)*12;market=train@anchor;excess=float(np.mean(market-rf_train)*12);var=float(np.var(market,ddof=1));beta=((train-train.mean(0)).T@(market-market.mean()))/((len(train)-1)*max(var,1e-12));capm=rf+beta*excess;residual=train-train.mean(0)-(market-market.mean())[:,None]*beta[None,:];capm_cov=12*(var*np.outer(beta,beta)+np.diag(np.var(residual,axis=0,ddof=1)))
    ew=np.power(.94,np.arange(len(train)-1,-1,-1));ew/=ew.sum();ewmean=ew@train;center=train-ewmean;ewcov=(center.T*ew)@center*12
    p,q,conf,corr,_=default_views(assets,anchor,regularized_mean(train),rf);bl=posterior(cov,anchor,delta,tau,p,q,conf,corr)
    pairs={'prior_only':(rf+bl['prior_excess'],cov*(1+tau)),'black_litterman':(rf+bl['posterior_excess'],bl['predictive_covariance']),'historical':(historic,cov),'capm':(capm,capm_cov),'ewma':(ewmean*12,ewcov)}
    actual_cov=np.atleast_2d(np.cov(test,rowvar=False,ddof=1))*12;out=[];equal=np.ones(len(assets))/len(assets)
    for name,(mu,sigma) in pairs.items():
        c,_=config(assets,cap,0.,mandate);engine=MeanVariance(mu,sigma,rf,c);r=engine.solve(return_weight=1.,variance_weight=lam,penalty=0.);errors=test-mu/12
        row={'id':name,'status':r['status'],'monthly_rmse':float(np.sqrt(np.mean(errors**2))),'monthly_mae':float(np.mean(abs(errors))),'covariance_rmse':float(np.sqrt(np.mean((sigma-actual_cov)**2))),'equal_weight_variance_forecast':float(equal@sigma@equal),'equal_weight_realized_variance':float(equal@actual_cov@equal)}
        if r['status']=='optimal':
            w=np.maximum(r['weights'],0);w/=w.sum();net=simulate(test,dates,w,cost_bps=cost);row|={'metrics':metrics(net['returns'],rf_test),'nav':[x['twr_index'] for x in net['ledger']],'fees':net['total_fees']}
        out.append(row)
    net=simulate(test,dates,equal,cost_bps=cost);out.append({'id':'equal_weight','status':'computed','metrics':metrics(net['returns'],rf_test),'nav':[x['twr_index'] for x in net['ledger']],'fees':net['total_fees']});return out


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);scope=data.get('scope','cohort');currency=data.get('currency','USD');tau=data.get('tau',.05);delta=data.get('delta');lam=data.get('risk_aversion',3.);cap=data.get('max_weight',.05 if scope=='cohort' else .65);cost=data.get('cost_bps',10.);anchor_kind=data.get('anchor','market_cap');mode=data.get('view_mode','automatic');mandate=data.get('mandate')
    if as_of>date.today() or scope not in ('cohort','core') or currency not in ('USD','CHF') or anchor_kind not in ('market_cap','equal_weight') or mode not in ('automatic','none','manual'):raise ValueError('Invalid BL settings')
    for v in (tau,lam,cap,cost,*([delta] if delta is not None else [])):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v):raise ValueError('Invalid BL numeric setting')
    if not 0<tau<=1 or not .01<=lam<=100 or not 0<cap<=1 or not 0<=cost<=200 or delta is not None and not 0<delta<=100:raise ValueError('BL setting out of range')
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,data_version=aligned(root,as_of,currency,scope);n=len(assets);w,anchor=market_anchor(root,assets,intervals[-1][1],scope,anchor_kind);lw=LedoitWolf().fit(x);cov=lw.covariance_*12;rfa=float(rf[-1]*12);de=delta_estimate(x,rf,w);d=de['delta'] if delta is None else float(delta)
        raw=np.array([v['expected_return'] for v in assets]) if currency=='USD' and scope=='cohort' else None;expected=regularized_mean(x,raw)
        if mode=='automatic':P,q,conf,corr,labels=default_views(assets,w,expected,rfa)
        elif mode=='manual':P,q,conf,corr,labels=manual_views(assets,data.get('views',[]),rfa)
        else:P,q,conf,corr,labels=np.empty((0,n)),np.array([]),np.array([]),np.empty((0,0)),[]
        if data.get('view_correlation') is not None:corr=data['view_correlation']
        bl=posterior(cov,w,d,tau,P,q,conf,corr);prior=bl['prior_excess']+rfa;post=bl['posterior_excess']+rfa;pred=bl['predictive_covariance'];c,unknown=config(assets,cap,0.,mandate)
        engine=MeanVariance(post,pred,rfa,c);base=MeanVariance(prior,cov*(1+tau),rfa,config(assets,cap,0.,mandate)[0]);before=base.solve(return_weight=1.,variance_weight=lam,penalty=0.);after=engine.solve(return_weight=1.,variance_weight=lam,penalty=0.,warm=before.get('weights'));minimum=engine.solve(penalty=0.);sharpe=engine.max_sharpe((minimum,[]))
        views=[{'label':label,'confidence':float(conf[i]),'q_excess':float(q[i]),'prior_view_excess':float(P[i]@bl['prior_excess']),'posterior_view_excess':float(P[i]@bl['posterior_excess']),'active':i in bl['active_views']} for i,label in enumerate(labels)]
        sensitivity=[]
        for dd in (1.,2.5,5.):
            b=posterior(cov,w,dd,tau,P,q,conf,corr);sensitivity.append({'delta':dd,'anchor_prior_excess':float(w@b['prior_excess']),'anchor_posterior_excess':float(w@b['posterior_excess'])})
        for tt in (.01,.05,.2):
            b=posterior(cov,w,d,tt,P,q,conf,corr);sensitivity.append({'tau':tt,'anchor_posterior_excess':float(w@b['posterior_excess']),'anchor_predictive_volatility':float(np.sqrt(w@b['predictive_covariance']@w))})
        # Manual current views never used in historical holdout; use train-only aggregate views.
        cut=int(.8*len(x));tw,ta=market_anchor(root,assets,intervals[cut-1][1],scope,anchor_kind);tr=x[:cut];tc=LedoitWolf().fit(tr).covariance_*12;td=delta_estimate(tr,rf[:cut],tw)['delta'] if delta is None else d;holdout=compare_models(tr,x[cut:],rf[:cut],rf[cut:],tw,tc,td,tau,assets,cap,lam,cost,intervals[cut:],mandate)
        rows=[{'id':a['id'],'ticker':a['ticker'],'category':a['category'],'market_weight':float(w[i]),'prior':float(prior[i]),'posterior':float(post[i]),'historical':float(x[:,i].mean()*12),'mean_uncertainty':float(np.sqrt(max(0,bl['mean_covariance'][i,i]))),'predictive_volatility':float(np.sqrt(max(0,pred[i,i])))} for i,a in enumerate(assets)]
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':data_version,'as_of':str(as_of),'currency':currency,'scope':scope,'assets':n,'observations':len(x),'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'anchor':anchor,'delta':d,'delta_diagnostics':de,'delta_override':delta is not None,'tau':tau,'lambda':lam,'cap':cap,'rf_annual':rfa,'reference_is_cash_proxy':currency=='CHF','view_mode':mode,'views':views,'omega':bl['omega'].tolist(),'view_rank':bl['rank'],'view_condition':bl['condition'],'view_residual':bl['residual'],'dropped_views':bl['dropped_views'],'assets_posterior':rows,'models':{'prior_utility':compact(before,assets),'posterior_utility':compact(after,assets),'posterior_minimum_variance':compact(minimum,assets),'posterior_maximum_sharpe':compact(sharpe,assets)},'sensitivity':sensitivity,'holdout':{'train_months':cut,'test_months':len(x)-cut,'first':str(intervals[cut][0]),'last':str(intervals[-1][1]),'anchor':ta,'rows':holdout,'view_rule':'training_only_aggregate_historical_views'},'unverified_mandate_constraints':unknown,'warning':'Restricted equity equilibrium proxy, not global market portfolio. Current cohort retrospectively selected; views/confidence are scenarios, not verified forecasts or suitability.'}


def cached_report(root,data):
    if data.get('mandate') is not None or data.get('view_mode','automatic')=='manual' or data.get('view_correlation') is not None:return run_report(root,data)
    root=Path(root);scope=data.get('scope','cohort');settings={'as_of':data['as_of'],'scope':scope,'currency':data.get('currency','USD'),'tau':data.get('tau',.05),'delta':data.get('delta'),'risk_aversion':data.get('risk_aversion',3.),'max_weight':data.get('max_weight',.05 if scope=='cohort' else .65),'cost_bps':data.get('cost_bps',10.),'anchor':data.get('anchor','market_cap'),'view_mode':data.get('view_mode','automatic')}
    for k in ('tau','delta','risk_aversion','max_weight','cost_bps'):
        if settings[k] is not None:
            if isinstance(settings[k],bool) or not isinstance(settings[k],(int,float)) or not np.isfinite(settings[k]):raise ValueError('Invalid numeric setting')
            settings[k]=float(settings[k])
    d=date.fromisoformat(settings['as_of']);r=returns_report(root,d);f=batch_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),settings],sort_keys=True).encode()).hexdigest();base=root/'data/processed/black_litterman';path=base/f'{key}.json'
    try:
        out=json.loads(path.read_text())
        if out['run_id']==key and out['version']==VERSION and out['data_version']==r['return_id']:return out
    except (OSError,ValueError,KeyError):pass
    out=run_report(root,settings)|{'run_id':key,'configuration':settings};base.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(out,f,allow_nan=False);tmp=Path(f.name)
    tmp.replace(path);return out
