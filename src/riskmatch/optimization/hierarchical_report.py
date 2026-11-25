"""Risk-budget allocations on verified matched research universes."""
from datetime import date
from pathlib import Path
import hashlib,json,tempfile
import numpy as np
from sklearn.covariance import LedoitWolf
from threadpoolctl import threadpool_limits
from scipy.cluster.hierarchy import cut_tree
from sklearn.metrics import adjusted_rand_score
from riskmatch.optimization.hierarchical import VERSION,risk_budget,hierarchy,hrp,herc,maximum_diversification,proportional_cap,describe,risk_contributions
from riskmatch.optimization.mean_variance import MeanVariance,Constraints
from riskmatch.optimization.mean_variance_report import aligned,config,category
from riskmatch.backtesting.baselines import simulate,metrics
from riskmatch.backtesting.baseline_report import WINDOWS
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report


def budgets_for(assets,mode,custom=None):
    n=len(assets)
    if custom is not None:
        if not isinstance(custom,dict) or set(custom)!={a['id'] for a in assets}:raise ValueError('Provide positive budgets for every eligible asset ID')
        b=np.array([custom[a['id']] for a in assets],float)
        if not np.isfinite(b).all() or np.any(b<=0) or not np.isclose(b.sum(),1):raise ValueError('Risk budgets must be positive and sum to one')
        return b
    if mode=='equal_asset':return np.ones(n)/n
    if mode=='equal_class':
        classes=[category(a) for a in assets];unique=set(classes);return np.array([1/(len(unique)*classes.count(k)) for k in classes])
    raise ValueError('Invalid risk budget mode')


def build_models(cov,assets,upper,method,k,budgets,include_maxdiv=True):
    n=len(assets);tree=hierarchy(cov,method,[a['id'] for a in assets]);labels=cut_tree(tree['linkage'],n_clusters=k).ravel();models={}
    def add(name,r,target=None):
        if r.get('status') not in ('optimal','constrained_optimal'):models[name]={k:v for k,v in r.items() if k not in ('weights','labels')};return
        raw=np.asarray(r['weights']);w,changed=proportional_cap(raw,upper);summary=describe(cov,w,target);row={key:v for key,v in r.items() if key not in ('weights','labels','cluster_weights','cluster_risk_shares','marginal_risk','risk_contributions','marginal','contributions','shares','budgets')};row|=summary;row|={'status':'capped_heuristic' if changed else ('heuristic' if name=='hrp' else r['status']),'weights':w,'cap_adjusted':changed or r['status']=='constrained_optimal','raw_max_weight':r.get('raw_max_weight',float(raw.max())),'cap_residual':max(0.,float(np.max(w-upper))),'cluster_weights':[float(w[labels==j].sum()) for j in np.unique(labels)],'cluster_risk_shares':[float(np.asarray(summary['shares'])[labels==j].sum()) for j in np.unique(labels)] if summary['shares'] is not None else None}
        models[name]=row
    add('risk_parity',risk_budget(cov,budgets,upper),budgets);add('hrp',{'status':'optimal','weights':hrp(cov,tree),'variant':'quasi_diagonal_recursive_bisection'});add('herc',herc(cov,tree,k,upper));
    if include_maxdiv:add('maximum_diversification',maximum_diversification(cov,upper))
    return models,tree,labels


def fit_cov(x):
    lw=LedoitWolf().fit(x);return lw.covariance_*12,float(lw.shrinkage_)


def compact_models(models,assets,labels,budgets):
    out={}
    for name,r in models.items():
        if 'weights' not in r:out[name]=r;continue
        w=r['weights'];rows=[{'id':a['id'],'ticker':a['ticker'],'category':a['category'],'cluster':int(labels[i])+1,'weight':float(w[i]),'risk_budget':float(budgets[i]) if name=='risk_parity' else None,'marginal_risk':r['marginal'][i] if r['marginal'] is not None else None,'risk_contribution':r['contributions'][i] if r['contributions'] is not None else None,'risk_share':r['shares'][i] if r['shares'] is not None else None} for i,a in enumerate(assets)]
        out[name]={k:v for k,v in r.items() if k not in ('weights','marginal','contributions','shares')}|{'holdings':rows,'top_weights':sorted(rows,key=lambda a:a['weight'],reverse=True)[:15]}
    return out


def holdout(x,rf,intervals,assets,upper,method,k,budgets,cost):
    split=int(.8*len(x));train=x[:split];test=x[split:];cov,_=fit_cov(train);models,tree,labels=build_models(cov,assets,upper,method,k,budgets);n=len(assets);eq,_=proportional_cap(np.ones(n)/n,upper);models['equal_weight']={'status':'reference','weights':eq};gmv=MeanVariance(np.zeros(n),cov,0,Constraints(np.zeros(n),upper)).solve(penalty=0.)
    if gmv['status']=='optimal':models['minimum_variance']={'status':'optimal','weights':np.asarray(gmv['weights'])}
    actual=np.atleast_2d(np.cov(test,rowvar=False,ddof=1))*12;out=[]
    for name,r in models.items():
        if 'weights' not in r:out.append({'id':name,'status':r['status'],'reason':r.get('reason')});continue
        w=r['weights'];net=simulate(test,intervals[split:],w,cost_bps=cost);gross=simulate(test,intervals[split:],w);rr=describe(actual,w,budgets if name=='risk_parity' else None);out.append({'id':name,'status':r['status'],'net':metrics(net['returns'],rf[split:]),'gross':metrics(gross['returns'],rf[split:]),'annual_turnover':net['annual_one_way_turnover'],'fees':net['total_fees'],'nav':[p['twr_index'] for p in net['ledger']],'realized_fixed_weight_risk':{k:v for k,v in rr.items() if k not in ('marginal','contributions','shares')},'realized_cluster_risk_shares':[float(np.asarray(rr['shares'])[labels==j].sum()) for j in np.unique(labels)] if rr['shares'] is not None else None})
    return {'train_months':split,'test_months':len(test),'first':str(intervals[split][0]),'last':str(intervals[-1][1]),'rows':out,'dates':[str(b) for a,b in intervals[split:]]}


def stress_windows(x,rf,intervals,assets,upper,method,k,budgets,cost):
    out={}
    for name,(start,end) in WINDOWS.items():
        ix=[i for i,(_,d) in enumerate(intervals) if start<=d<=end];expected=(end.year-start.year)*12+end.month-start.month+1
        if len(ix)!=expected or ix[0]<24:out[name]={'status':'unavailable','reason':'Incomplete crisis window or fewer than 24 prior months'};continue
        cov,_=fit_cov(x[:ix[0]]);models,_,_=build_models(cov,assets,upper,method,k,budgets);rows=[]
        for key,r in models.items():
            if 'weights' not in r:rows.append({'id':key,'status':r['status']});continue
            a=simulate(x[ix], [intervals[i] for i in ix],r['weights'],cost_bps=cost);rows.append({'id':key,'status':r['status'],'net_cumulative':float(np.prod(1+np.asarray(a['returns']))-1),'max_drawdown':metrics(a['returns'],rf[ix])['max_drawdown']})
        out[name]={'status':'experimental','training_months':ix[0],'months':len(ix),'rows':rows}
    return out


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);scope=data.get('scope','cohort');currency=data.get('currency','USD');method=data.get('linkage','average');k=data.get('clusters',8 if scope=='cohort' else 3);cap=data.get('max_weight',.05 if scope=='cohort' else .65);cost=data.get('cost_bps',10.);budget_mode=data.get('budget_mode','equal_asset');mandate=data.get('mandate');custom=data.get('risk_budgets')
    if as_of>date.today() or scope not in ('cohort','core') or currency not in ('USD','CHF') or method not in ('single','average','complete') or isinstance(k,bool) or not isinstance(k,int) or not 2<=k<=30 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in (cap,cost)) or not 0<cap<=1 or not 0<=cost<=200:raise ValueError('Invalid hierarchy settings')
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);c,unknown=config(assets,cap,0.,mandate);idx=np.flatnonzero(c.upper>0);upper=c.upper[idx];assets=[assets[i] for i in idx];x=x[:,idx];n=len(assets)
        if n<2 or upper.sum()<1-1e-10:return {'status':'infeasible','reason':'Insufficient eligible capacity','assets':n,'unverified_mandate_constraints':unknown}
        if k>n:return {'status':'infeasible','reason':'Cluster count exceeds eligible assets','assets':n}
        budgets=budgets_for(assets,budget_mode,custom);cov,shrink=fit_cov(x);models,tree,labels=build_models(cov,assets,upper,method,k,budgets);sensitivity=[]
        for link,kk in [(v,k) for v in ('single','average','complete')]+[(method,q) for q in sorted({max(2,k-2),min(n,k+2)}) if q!=k]:
            t=hierarchy(cov,link);l=cut_tree(t['linkage'],n_clusters=kk).ravel();h=herc(cov,t,kk,upper);hw,changed=proportional_cap(h['weights'],upper) if 'weights'in h else (None,False);v=describe(cov,hw) if hw is not None else {};base=models.get('herc',{}).get('weights');sensitivity.append({'linkage':link,'clusters':kk,'adjusted_rand_index':float(adjusted_rand_score(labels,l)),'herc_status':'capped_heuristic' if changed else h['status'],'herc_volatility':v.get('volatility'),'weight_distance':float(np.abs(hw-base).sum()/2) if hw is not None and base is not None else None})
        clusters=[{'id':int(j)+1,'size':int((labels==j).sum()),'members':[a['ticker'] for a,u in zip(assets,labels) if u==j]} for j in np.unique(labels)]
        hist=holdout(x,rf,intervals,assets,upper,method,k,budgets,cost);stress=stress_windows(x,rf,intervals,assets,upper,method,k,budgets,cost)
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'as_of':str(as_of),'scope':scope,'currency':currency,'asset_count':n,'observations':len(x),'start':str(intervals[0][0]),'end':str(intervals[-1][1]),'shrinkage':shrink,'linkage':method,'cluster_count':len(clusters),'budget_mode':budget_mode,'cap':cap,'cost_bps':cost,'tree':{'links':tree['linkage'].tolist(),'order':tree['order'].tolist(),'labels':[a['ticker'] for a in assets],'cluster_labels':(labels+1).tolist(),'duplicate_pair_count':tree['duplicate_pair_count']},'clusters':clusters,'models':compact_models(models,assets,labels,budgets),'sensitivity':sensitivity,'holdout':hist,'stress':stress,'reference_is_cash_proxy':currency=='CHF','unverified_mandate_constraints':unknown,'warning':'Research only. Capped HRP/HERC/ERC proportional redistribution is heuristic and may deviate from target risk budgets. Retrospective cohort selection; original publication/execution unverified.'}


def cached_report(root,data):
    if data.get('mandate') is not None or data.get('risk_budgets') is not None:return run_report(root,data)
    root=Path(root);scope=data.get('scope','cohort');settings={'as_of':data['as_of'],'scope':scope,'currency':data.get('currency','USD'),'linkage':data.get('linkage','average'),'clusters':data.get('clusters',8 if scope=='cohort' else 3),'max_weight':data.get('max_weight',.05 if scope=='cohort' else .65),'cost_bps':data.get('cost_bps',10.),'budget_mode':data.get('budget_mode','equal_asset')}
    for k in ('max_weight','cost_bps'):
        if isinstance(settings[k],bool) or not isinstance(settings[k],(int,float)) or not np.isfinite(settings[k]):raise ValueError('Invalid numeric field')
        settings[k]=float(settings[k])
    d=date.fromisoformat(settings['as_of']);r=returns_report(root,d);f=batch_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),settings],sort_keys=True).encode()).hexdigest();base=root/'data/processed/hierarchical';path=base/f'{key}.json'
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
