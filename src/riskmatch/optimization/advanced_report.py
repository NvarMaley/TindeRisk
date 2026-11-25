"""Advanced research defaults, disjoint train/test and same funded ledger."""
from time import perf_counter
from datetime import date
from pathlib import Path
import hashlib,json,tempfile
import numpy as np
from threadpoolctl import threadpool_limits
from riskmatch.optimization.advanced import VERSION,uncertainty,quadratic,robust_utility,resampled_utility,wasserstein_utility,kelly,entropy_utility
from riskmatch.optimization.mean_variance_report import aligned,config,category
from riskmatch.optimization.mean_variance import MeanVariance,Constraints
from riskmatch.optimization.hierarchical import proportional_cap,describe
from riskmatch.backtesting.baselines import simulate,metrics
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report

GOOD=('optimal','aggregated_feasible','feasible_blend','reference')

def timed(fn,*a,**kw):
    t=perf_counter();r=fn(*a,**kw);r.setdefault('runtime_seconds',perf_counter()-t);return r

def stress_vector(assets):
    special={'BIL':0.,'SHY':-.03,'IEF':-.10,'TIP':-.10,'TLT':-.15}
    return np.array([special.get(a['ticker'],-.30 if category(a) in ('equity','reit') else -.10 if category(a)=='treasury' else -.20) for a in assets])

def fractional(full,x,upper,ref,fraction,floor,assets):
    if full.get('status')!='optimal':return {'status':'unavailable','reason':'Full Kelly not certified'}
    w=np.asarray(full['weights']);b=np.zeros(len(w));ids=[i for i,a in enumerate(assets) if a['ticker']=='BIL' and a['source']=='etf_crsp_monthly'];kind='capped_minimum_variance_defensive_reference'
    if len(ids)==1:
        b[ids[0]]=1;q=fraction*w+(1-fraction)*b
        if np.all(q<=upper+1e-9) and np.min(1+x@q)>=floor-1e-9:kind='BIL_cash_proxy';ref=b
    q=fraction*w+(1-fraction)*ref;wealth=1+x@q;res=max(abs(q.sum()-1),float(np.maximum(q-upper,0).max()),float(np.maximum(-q,0).max()))
    if res>2e-7 or wealth.min()<floor-2e-7:return {'status':'infeasible','reason':'Fractional blend violates caps or wealth floor'}
    return {'status':'feasible_blend','weights':q.tolist(),'reference':kind,'fraction':fraction,'classic_cash_blend':kind=='BIL_cash_proxy','minimum_scenario_wealth':float(wealth.min()),'annual_log_growth':float(12*np.log(wealth).mean()),'residual':res,'solver':'convex feasible blend'}

def fit_all(x,assets,u,s):
    ref,_=proportional_cap(np.ones(len(u))/len(u),u);mu,cov,half,radius,means,covs=uncertainty(x,s['draws'],seed=17);eps=float(np.quantile(np.linalg.norm(means-mu,axis=1),.9));shock=stress_vector(assets);scen=np.vstack([x,shock]);lam=s['risk_aversion'];p=s['turnover_penalty'];scale=s['uncertainty_scale'];dro=s['wasserstein_scale'];m={}
    m['nominal_utility']=timed(quadratic,mu,cov,u,lam,p,ref);m['robust_utility']=timed(robust_utility,mu,cov,half*scale,radius*scale,u,lam,p,ref);m['resampled_efficient']=timed(resampled_utility,means,covs,u,lam,p,ref);m['distributionally_robust']=timed(wasserstein_utility,mu,cov,eps*dro,u,lam,p,ref);m['kelly']=timed(kelly,scen,u,p,ref,s['wealth_floor']);gmv=timed(MeanVariance(np.zeros(len(u)),cov,0,Constraints(np.zeros(len(u)),u)).solve,penalty=0.);defense=np.asarray(gmv['weights']) if gmv['status']=='optimal' else ref
    m['fractional_kelly']=timed(fractional,m['kelly'],scen,u,defense,s['kelly_fraction'],s['wealth_floor'],assets);m['entropy_utility']=timed(entropy_utility,mu,cov,s['entropy_weight'],u,lam,p,ref);m['maximum_entropy']={'status':'reference','weights':ref.tolist(),'solver':'analytic capped equal weight','runtime_seconds':0.};m['minimum_variance']=gmv
    return m,mu,cov,half,radius,eps,means,covs,ref,shock

def compact(models,assets,mu,cov,shock,ref):
    out={}
    for key,r in models.items():
        if 'weights' not in r:out[key]=r;continue
        w=np.asarray(r['weights']);d=describe(cov,w);h=[{'id':a['id'],'ticker':a['ticker'],'category':a['category'],'weight':float(w[i]),'weight_std':r.get('weight_std',[None]*len(w))[i],'risk_share':d['shares'][i] if d['shares'] is not None else None} for i,a in enumerate(assets)];row={k:v for k,v in r.items() if k not in ('weights','weight_std','marginal_risk','risk_contributions','volatility','variance','sharpe','expected_return')};row|={'nominal_expected_return':float(mu@w),'volatility':d['volatility'],'effective_positions':d['effective_positions'],'nonzero_count':d['nonzero_count'],'entropy':float(-np.sum(w[w>0]*np.log(w[w>0]))),'stress_loss':float(-shock@w),'turnover_vs_reference':float(np.abs(w-ref).sum()/2),'holdings':h,'top_weights':sorted(h,key=lambda a:a['weight'],reverse=True)[:15]};out[key]=row
    return out

def settings(data):
    scope=data.get('scope','cohort');defaults={'as_of':data['as_of'],'scope':scope,'currency':'USD','max_weight':.05 if scope=='cohort' else .65,'risk_aversion':3.,'turnover_penalty':.001,'cost_bps':10.,'draws':8,'uncertainty_scale':1.,'wasserstein_scale':.25,'entropy_weight':.03,'kelly_fraction':.5,'wealth_floor':.01};s={k:data.get(k,v) for k,v in defaults.items()}
    for k in defaults:
        if k not in ('as_of','scope','currency','draws'):
            if isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not np.isfinite(s[k]):raise ValueError('Invalid numeric inputs')
            s[k]=float(s[k])
    if date.fromisoformat(s['as_of'])>date.today() or s['scope'] not in ('cohort','core') or s['currency'] not in ('USD','CHF') or isinstance(s['draws'],bool) or not isinstance(s['draws'],int) or not 4<=s['draws']<=24:raise ValueError('Invalid advanced settings')
    bounds={'max_weight':(1e-6,1),'risk_aversion':(.01,100),'turnover_penalty':(0,.1),'cost_bps':(0,200),'uncertainty_scale':(0,5),'wasserstein_scale':(0,5),'entropy_weight':(0,1),'kelly_fraction':(0,1),'wealth_floor':(1e-6,.99)}
    if any(not lo<=s[k]<=hi for k,(lo,hi) in bounds.items()):raise ValueError('Advanced setting outside range')
    return s

def run_report(root,data):
    start=perf_counter();s=settings(data);as_of=date.fromisoformat(s['as_of']);mandate=data.get('mandate');scope=s['scope'];currency=s['currency'];cap=s['max_weight'];lam=s['risk_aversion'];p=s['turnover_penalty'];cost=s['cost_bps']
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);c,unknown=config(assets,cap,p,mandate);u=c.upper;n=len(assets)
        if u.sum()<1-1e-10:return {'status':'infeasible','reason':'Insufficient eligible funded capacity','asset_count':n}
        models,mu,cov,half,radius,eps,means,covs,ref,shock=fit_all(x,assets,u,s);sensitivity=[];base=models['nominal_utility'].get('weights')
        for scale in (0.,.5,2.):
            for key,r in [('robust_utility',timed(robust_utility,mu,cov,half*scale,radius*scale,u,lam,p,ref)),('distributionally_robust',timed(wasserstein_utility,mu,cov,eps*scale,u,lam,p,ref))]:
                w=np.asarray(r['weights']) if r['status']=='optimal' else None;sensitivity.append({'method':key,'scale':scale,'status':r['status'],'expected_return':float(mu@w) if w is not None else None,'volatility':float(np.sqrt(w@cov@w)) if w is not None else None,'distance_to_nominal':float(np.abs(w-base).sum()/2) if w is not None and base is not None else None,'runtime_seconds':r['runtime_seconds']})
        frontier=[]
        for l in (1.,3.,10.):
            r=models['resampled_efficient'] if l==lam else resampled_utility(means,covs,u,l,p,ref);w=np.asarray(r['weights']) if r['status']=='aggregated_feasible' else None;frontier.append({'lambda':l,'status':r['status'],'expected_return':float(mu@w) if w is not None else None,'volatility':float(np.sqrt(w@cov@w)) if w is not None else None,'draws':s['draws']})
        cut=int(.8*len(x));test=x[cut:];dates=intervals[cut:];o,*_=fit_all(x[:cut],assets,u,s);o['equal_weight']={'status':'reference','weights':ref.tolist()};hold=[]
        for key,r in o.items():
            if r.get('status') not in GOOD or 'weights' not in r:hold.append({'id':key,'status':r['status'],'reason':r.get('reason')});continue
            w=np.asarray(r['weights']);net=simulate(test,dates,w,cost_bps=cost);gross=simulate(test,dates,w);rr=np.asarray(net['returns']);hold.append({'id':key,'status':r['status'],'net':metrics(rr,rf[cut:]),'gross':metrics(gross['returns'],rf[cut:]),'annual_turnover':net['annual_one_way_turnover'],'fees':net['total_fees'],'stress_loss_training_fitted':float(-shock@w),'worst_heldout_month':float(rr.min()),'minimum_test_wealth_multiplier':float((1+test@w).min()),'nav':[q['twr_index'] for q in net['ledger']]})
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'as_of':str(as_of),'scope':scope,'currency':currency,'asset_count':n,'observations':len(x),'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'configuration':s,'block_months':3,'seed':17,'mean_half_width_quantiles':np.quantile(half*s['uncertainty_scale'],[0,.5,.9,1]).tolist(),'covariance_radius':radius*s['uncertainty_scale'],'wasserstein_radius':eps*s['wasserstein_scale'],'wasserstein_base_radius':eps,'models':compact(models,assets,mu,cov,shock,ref),'sensitivity':sensitivity,'resampled_utility_frontier':frontier,'holdout':{'train_months':cut,'test_months':len(test),'first':str(dates[0][0]),'last':str(dates[-1][1]),'rows':hold},'reference_is_cash_proxy':currency=='CHF','unverified_mandate_constraints':unknown,'runtime_seconds':perf_counter()-start,'warning':'Retrospective research. Wasserstein ambiguity adjusts mean only, covariance nominal; fractional Kelly may use capped defensive reference. No suitability or execution certification.'}

def cached_report(root,data):
    if data.get('mandate') is not None:return run_report(root,data)
    root=Path(root);s=settings(data);d=date.fromisoformat(s['as_of']);r=returns_report(root,d);f=batch_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),s],sort_keys=True).encode()).hexdigest();base=root/'data/processed/advanced';path=base/f'{key}.json'
    try:
        out=json.loads(path.read_text())
        if out['run_id']==key and out['version']==VERSION and out['data_version']==r['return_id']:return out
    except (OSError,ValueError,KeyError):pass
    out=run_report(root,s)|{'run_id':key}
    if out['status']=='experimental':
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(out,f,allow_nan=False);tmp=Path(f.name)
        tmp.replace(path)
    return out
