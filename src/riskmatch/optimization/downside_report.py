"""Six downside / relative-risk methods; matched scenarios and costed holdout."""
from datetime import date
from pathlib import Path
import hashlib,json,tempfile
import numpy as np
from scipy.optimize import linprog
from sklearn.covariance import LedoitWolf
from threadpoolctl import threadpool_limits
from riskmatch.optimization.downside import VERSION,stats,cvar,cdar,omega,sortino,benchmark_models
from riskmatch.optimization.mean_variance_report import aligned,config,category
from riskmatch.optimization.hierarchical import proportional_cap
from riskmatch.backtesting.baselines import simulate,metrics
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report


def benchmark_vector(assets,name):
    n=len(assets);w=np.zeros(n)
    if name=='equal_weight':return np.ones(n)/n
    def get(t):
        ix=[i for i,a in enumerate(assets) if a['ticker']==t and a['source']=='etf_crsp_monthly']
        if len(ix)!=1:raise ValueError('Benchmark identity unavailable: '+t)
        return ix[0]
    if name=='spy':w[get('SPY')]=1
    elif name=='sixty_forty':w[get('SPY')]=.6;w[get('IEF')]=.4
    else:raise ValueError('Invalid benchmark')
    return w


def fit(x,u,b,alpha,mar):
    cov=LedoitWolf().fit(x).covariance_*12;te,ir=benchmark_models(x,u,b,cov)
    return {'minimum_cvar':cvar(x,u,alpha),'maximum_sortino':sortino(x,u,mar),'maximum_omega':omega(x,u,mar),'minimum_cdar':cdar(x,u,alpha),'minimum_tracking_error':te,'maximum_information_ratio':ir}


def pack(models,x,b,assets,alpha,mar):
    out={}
    for k,v in models.items():
        if 'weights' not in v:out[k]=v;continue
        w=np.asarray(v['weights']);s=stats(x@w,mar,x@b,alpha);h=[{'id':a['id'],'ticker':a['ticker'],'category':a['category'],'weight':float(w[i]),'benchmark_weight':float(b[i]),'active_weight':float(w[i]-b[i])} for i,a in enumerate(assets)];r={k:z for k,z in v.items() if k not in ('weights','marginal_risk','risk_contributions','sharpe','expected_return','variance','volatility')};
        out[k]=r|{'sample':s,'holdings':h,'top_weights':sorted(h,key=lambda h:h['weight'],reverse=True)[:15],'top_active':sorted(h,key=lambda h:abs(h['active_weight']),reverse=True)[:15],'nonzero_count':int((w>1e-6).sum()),'active_share':float(np.abs(w-b).sum()/2),'risk_model_tracking_error':v.get('volatility') if k in ('minimum_tracking_error','maximum_information_ratio') else None,'risk_model_information_ratio':v.get('sharpe') if k=='maximum_information_ratio' else None}
    return out


def sensitivity(x,u,alpha,mar,assets,base):
    n=len(x);rng=np.random.default_rng(17);block=3;size=300;starts=rng.integers(0,n-block+1,(size+block-1)//block);ix=(starts[:,None]+np.arange(block)).ravel()[:size];boot=x[ix];shock=np.array([-.30 if category(a) in ('equity','reit') else -.10 if category(a)=='treasury' else -.20 for a in assets]);prob=np.r_[np.full(n,.95/n),.05];stress=np.vstack((x,shock));out=[]
    for name,scenario,level,p in [('historical_90',x,.90,None),('historical_99',x,.99,None),('block_resample',boot,alpha,None),('hypothetical_shock_5pct',stress,alpha,prob)]:
        r=cvar(scenario,u,level,p);w=np.asarray(r['weights']) if r['status']=='optimal' else None;out.append({'id':name,'status':r['status'],'scenarios':len(scenario),'alpha':level,'effective_equal_weight_tail_count':len(scenario)*(1-level) if p is None else None,'scenario_cvar':r.get('cvar'),'historical_cvar':stats(x@w,mar,alpha=alpha)['cvar'] if w is not None else None,'weight_distance':float(np.abs(w-np.asarray(base['weights'])).sum()/2) if w is not None and 'weights'in base else None})
    return out


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);scope=data.get('scope','cohort');currency=data.get('currency','USD');alpha=data.get('alpha',.95);mar_annual=data.get('mar_annual',0.);cap=data.get('max_weight',.05 if scope=='cohort' else .65);cost=data.get('cost_bps',10.);bench=data.get('benchmark','spy');mandate=data.get('mandate')
    if as_of>date.today() or scope not in ('cohort','core') or currency not in ('USD','CHF') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in (alpha,mar_annual,cap,cost)) or not .5<=alpha<1 or not -.99<mar_annual<=1 or not 0<cap<=1 or not 0<=cost<=200:raise ValueError('Invalid downside settings')
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    mar=(1+mar_annual)**(1/12)-1
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);c,unknown=config(assets,cap,0.,mandate);u=c.upper;b=benchmark_vector(assets,bench);n=len(assets)
        if u.sum()<1-1e-10:return {'status':'infeasible','reason':'Insufficient eligible funded capacity','asset_count':n}
        models=fit(x,u,b,alpha,mar);mu=x.mean(0);maxr=linprog(-mu,A_eq=np.ones((1,n)),b_eq=[1],bounds=list(zip(np.zeros(n),u)),method='highs');front=[];mv=models['minimum_cvar']
        if mv['status']=='optimal':
            low=float(mu@np.asarray(mv['weights']));high=-float(maxr.fun)
            for t in np.linspace(low,high,9):
                r=cvar(x,u,alpha,target=float(t));front.append({'target':float(t),'status':r['status'],'period_mean':float(mu@np.asarray(r['weights'])) if r['status']=='optimal' else None,'cvar':r.get('cvar')})
            unreachable=cvar(x,u,alpha,target=high+.01)['status']
        else:unreachable='unavailable'
        sens=sensitivity(x,u,alpha,mar,assets,mv);cut=int(.8*len(x));train=x[:cut];test=x[cut:];dates=intervals[cut:];test_rf=rf[cut:];o=fit(train,u,b,alpha,mar);eq,_=proportional_cap(np.ones(n)/n,u);o['equal_weight']={'status':'reference','weights':eq.tolist()};o['benchmark']={'status':'reference','weights':b.tolist()};hold=[];benchmark_returns=test@b
        for key,r in o.items():
            if r.get('status') not in ('optimal','reference','zero_downside') or 'weights' not in r:hold.append({'id':key,'status':r['status'],'reason':r.get('reason')});continue
            w=np.asarray(r['weights']);w=np.maximum(w,0);w/=w.sum();net=simulate(test,dates,w,cost_bps=cost if key!='benchmark' else 0.);gross=simulate(test,dates,w);rr=np.asarray(net['returns']);hold.append({'id':key,'status':r['status'],'net':metrics(rr,test_rf),'gross':metrics(gross['returns'],test_rf),'downside':stats(rr,mar,benchmark_returns,alpha),'annual_turnover':net['annual_one_way_turnover'],'fees':net['total_fees']})
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'as_of':str(as_of),'asset_count':n,'scope':scope,'currency':currency,'observations':len(x),'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'alpha':alpha,'mar_annual':mar_annual,'mar_monthly':mar,'cap':cap,'cost_bps':cost,'benchmark':bench,'benchmark_weights':[{a['ticker']:float(b[i])} for i,a in enumerate(assets) if b[i]>1e-10],'scenario_probabilities':'equal historical months','tail_observation_equivalent':len(x)*(1-alpha),'models':pack(models,x,b,assets,alpha,mar),'frontier':front,'infeasible_target_test':unreachable,'scenario_sensitivity':sens,'holdout':{'train_months':cut,'test_months':len(test),'first':str(dates[0][0]),'last':str(dates[-1][1]),'dates':[str(d[1]) for d in dates],'rows':hold,'tail_observation_equivalent':len(test)*(1-alpha)},'reference_is_cash_proxy':currency=='CHF','unverified_mandate_constraints':unknown,'warning':'Research only; additive CDaR objective differs from compounded drawdown. Sample tails and ratios unstable; static endpoint universe retrospective. Benchmark gross theoretical monthly rebalance, zero fees; candidate fees modeled. No suitability or executable price certification.'}


def cached_report(root,data):
    if data.get('mandate') is not None:return run_report(root,data)
    root=Path(root);scope=data.get('scope','cohort');settings={'as_of':data['as_of'],'scope':scope,'currency':data.get('currency','USD'),'alpha':data.get('alpha',.95),'mar_annual':data.get('mar_annual',0.),'max_weight':data.get('max_weight',.05 if scope=='cohort' else .65),'cost_bps':data.get('cost_bps',10.),'benchmark':data.get('benchmark','spy')}
    for k in ('alpha','mar_annual','max_weight','cost_bps'):
        if isinstance(settings[k],bool) or not isinstance(settings[k],(int,float)) or not np.isfinite(settings[k]):raise ValueError('Invalid numeric field')
        settings[k]=float(settings[k])
    d=date.fromisoformat(settings['as_of']);r=returns_report(root,d);f=batch_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),settings],sort_keys=True).encode()).hexdigest();base=root/'data/processed/downside';path=base/f'{key}.json'
    try:
        out=json.loads(path.read_text())
        if out['run_id']==key and out['version']==VERSION and out['data_version']==r['return_id']:return out
    except (OSError,ValueError,KeyError):pass
    out=run_report(root,settings)|{'run_id':key,'configuration':settings}
    if out['status']=='experimental':
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(out,f,allow_nan=False);tmp=Path(f.name)
        tmp.replace(path)
    return out
