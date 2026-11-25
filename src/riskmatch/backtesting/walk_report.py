"""Local walk-forward orchestration, dated eligibility and experiment registry."""
from datetime import date,datetime,timezone
from pathlib import Path
import hashlib,json,tempfile
import duckdb
import numpy as np
from threadpoolctl import threadpool_limits
from riskmatch.backtesting.walk_forward import VERSION,folds,ledger,summarize,bootstrap_comparison
from riskmatch.backtesting.walk_models import REGISTRY,TUNABLE,SIGNED,fit_models
from riskmatch.optimization.mean_variance_report import aligned,config
from riskmatch.strategies.long_only_report import verified_pit,load_signals
from riskmatch.strategies.alternative_report import macro_signals
from riskmatch.backtesting.baselines import metrics
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.analytics.factor_report import factor_report

UNSUPPORTED={'managed_futures':'Chapter 22 archived conditional ledger only; no certified rolls/settlements/margins','carry':'Instrument-level carry and financing history unavailable','tail_hedging':'Dated futures and actual margin unavailable','individual_treasuries':'Chapter 21 separate coupon/indexation ledger; no certified common monthly total-return prices','fama_french':'Factor risk/return analysis in Chapter 10; dated complete cross-asset factor forecasts not integrated here','forecast_ml':'Chapter 8 asset-level train/validation/test; common dated rolling forecast matrix not available; current forecast vector explicitly excluded'}


def settings(data):
    scope=data.get('scope','core');currency=data.get('currency','USD');s={'as_of':data['as_of'],'scope':scope,'currency':currency,'mode':data.get('mode','rolling'),'train':data.get('train',24 if currency=='CHF' else 36),'validation':data.get('validation',6 if currency=='CHF' else 12),'step':data.get('step',12 if scope=='core' and currency=='USD' else 6),'embargo':data.get('embargo',1),'delay':data.get('delay',1),'cost_bps':data.get('cost_bps',10.),'spread_bps':data.get('spread_bps',0.),'slippage_bps':data.get('slippage_bps',0.),'capital':data.get('capital',100000.),'max_weight':data.get('max_weight',.65 if scope=='core' else .05),'turnover_limit':data.get('turnover_limit',1.),'optimizer_limit':data.get('optimizer_limit',64),'seed':data.get('seed',23),'selected':data.get('selected','mean_variance_utility')}
    if date.fromisoformat(s['as_of'])>date.today() or scope not in ('core','cohort') or currency not in ('USD','CHF') or s['mode'] not in ('rolling','expanding') or s['selected'] not in REGISTRY:raise ValueError('Invalid walk-forward request')
    for k,lo,hi in [('train',18,120),('validation',4,36),('step',2,24),('embargo',0,3),('delay',1,3),('optimizer_limit',32,128),('seed',0,2**31-1)]:
        v=s[k]
        if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:raise ValueError('Invalid integer setting: '+k)
    for k,lo,hi in [('cost_bps',0,100),('spread_bps',0,50),('slippage_bps',0,50),('capital',1,1e9),('max_weight',.001,1),('turnover_limit',0,1)]:
        v=s[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid numeric setting: '+k)
        s[k]=float(v)
    return s


def run(root,s,mandate=None):
    as_of=date.fromisoformat(s['as_of']);scope=s['scope'];currency=s['currency'];cost=s['cost_bps']+s['spread_bps']/2+s['slippage_bps'];seed=s['seed'];delay=s['delay'];capital=s['capital'];turn=s['turnover_limit']
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);n=len(x);k=len(assets);ff,hold=folds(n,s['train'],s['validation'],s['step'],s['embargo'],s['mode']);first=ff[0].decision;origins=[a for a,b in intervals];c,unknown=config(assets,s['max_weight'],0.,mandate);base=c.upper;stock=np.array([a['source']=='stock_monthly' for a in assets]);spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY');ief=next(i for i,a in enumerate(assets) if a['ticker']=='IEF');bil=next(i for i,a in enumerate(assets) if a['ticker']=='BIL')
        if mandate and mandate['constraints']['max_turnover']['mode']=='hard' and mandate['constraints']['max_turnover']['value'] is not None:turn=min(turn,mandate['constraints']['max_turnover']['value'])
        signals=load_signals(root,as_of,assets,origins,version);membership=signals[0];caps={}
        if stock.any():
            p=verified_pit(root,version)
            with duckdb.connect() as db:
                records=db.execute('select instrument,observation_date,market_cap_source_units from read_parquet(?) where observation_date in (select unnest(?)) and instrument in (select unnest(?)) and market_cap_source_units>0',[str(p/'stock_membership.parquet'),origins,[str(a['instrument']) for a in assets if a['source']=='stock_monthly']]).fetchall()
            for i,d,v in records:caps.setdefault(d,{})[str(i)]=float(v)
        upper=np.tile(base,(n,1));
        for j,day in enumerate(origins):
            if stock.any():upper[j,stock]=[base[i] if str(assets[i]['instrument']) in membership.get(day,set()) else 0. for i in np.flatnonzero(stock)]
        macro=macro_signals(root,version,origins);model_keys=list(REGISTRY);plans={key:{} for key in model_keys};failures={key:[] for key in model_keys};fold_rows=[];locked_params={};locked_model=None;locked_selection={}
        def strategy_ledger(key,*args,**kwargs):
            if key in SIGNED and mandate:return {'status':'unavailable','reason':'Signed research cannot certify client short, borrow, collateral and mandate gross/net constraints'}
            return ledger(*args,**kwargs,signed=key in SIGNED)
        for fidx,f in enumerate(ff):
            # Initial train→validation is disjoint with an embargo. Fit at the last train close.
            vi=f.validation_start;ti=f.train_end-1;day=origins[vi];train=x[f.train_start:f.train_end];trf=rf[f.train_start:f.train_end];vx=x[vi:f.validation_end];vrf=rf[vi:f.validation_end];vdates=intervals[vi:f.validation_end];vu=upper[vi:f.validation_end]
            validate_all=f.phase=='development' or not locked_params
            trials={};params={};best_scores={}
            if validate_all:
                fit=fit_models(model_keys,train,trf,assets,upper[vi],day,signals,optimizer_limit=s['optimizer_limit'],market_caps=caps.get(day),lam=3.,seed=seed+fidx,macro=macro.get(day));tuned={lam:fit_models(TUNABLE,train,trf,assets,upper[vi],day,signals,optimizer_limit=s['optimizer_limit'],market_caps=caps.get(day),lam=lam,seed=seed+fidx,macro=macro.get(day)) for lam in (1.,10.)}
                for key in model_keys:
                    choices=[(3.,fit[key])]+([(a,tuned[a][key]) for a in (1.,10.)] if key in TUNABLE else []);history=[];best=None
                    for lam,row in choices:
                        if row['status']!='computed':history.append({'parameter':lam,'status':'unavailable','reason':row.get('reason')});continue
                        sim=strategy_ledger(key,vx,vrf,vdates,{0:row['weights']},vu,capital=capital,cost_bps=cost,delay=delay,turnover_limit=turn)
                        if sim['status']!='computed':history.append({'parameter':lam,'status':'unavailable','reason':sim.get('reason')});continue
                        r=sim['returns'];excess=r-vrf;score=float(excess.mean()*12-1.5*np.var(excess,ddof=1)*12);history.append({'parameter':lam,'status':'computed','validation_score':score,'validation_cumulative':float(np.prod(1+r)-1)})
                        if best is None or score>best[0]:best=(score,lam)
                    trials[key]=history
                    if best:params[key]=best[1];best_scores[key]=best[0]
                    else:params[key]=3.
                if f.phase=='locked_holdout':
                    locked_params=params.copy();locked_selection=best_scores.copy();locked_model=max(best_scores,key=best_scores.get) if best_scores else None
            else:params=locked_params.copy()
            # Refit through validation end, never the embargo or future test observations.
            day=origins[f.decision];h=x[f.train_start:f.validation_end];h_rf=rf[f.train_start:f.validation_end];fit=fit_models(model_keys,h,h_rf,assets,upper[f.decision],day,signals,optimizer_limit=s['optimizer_limit'],market_caps=caps.get(day),lam=3.,seed=seed+fidx,macro=macro.get(day));
            for lam in (1.,10.):
                keys=[key for key in TUNABLE if params.get(key)==lam]
                if keys:fit.update(fit_models(keys,h,h_rf,assets,upper[f.decision],day,signals,optimizer_limit=s['optimizer_limit'],market_caps=caps.get(day),lam=lam,seed=seed+fidx,macro=macro.get(day)))
            diagnostics={}
            for key in model_keys:
                row=fit[key];diagnostics[key]={'status':row['status'],'parameter':params.get(key,3.),'candidate_count':row.get('candidate_count'),'reason':row.get('reason')}
                if row['status']=='computed':plans[key][f.decision-first]=row['weights']
                else:failures[key].append({'decision':str(day),'phase':f.phase,'reason':row.get('reason')})
            fold_rows.append({'phase':f.phase,'train_start':str(origins[f.train_start]),'train_end':str(intervals[f.train_end-1][1]),'validation_start':str(origins[vi]),'validation_end':str(intervals[f.validation_end-1][1]),'decision':str(day),'scheduled_execution':str(origins[f.decision+delay]) if f.decision+delay<n else None,'test_end':str(intervals[f.test_end-1][1]),'train_months':f.train_end-f.train_start,'validation_months':f.validation_end-vi,'test_months':f.test_end-f.decision,'validation_trials':trials,'models':diagnostics})
        xx=x[first:];rr=rf[first:];dates=intervals[first:];uu=upper[first:];lock=hold-first;all_caps=np.ones_like(uu);b_spy=np.zeros(k);b_spy[spy]=1;b_60=np.zeros(k);b_60[spy]=.6;b_60[ief]=.4;b_eq=np.ones(k)/k;b_cash=np.zeros(k)
        # Same delay, fee convention and start as tested strategies; benchmark cap exemption.
        reference={};ref_returns={}
        for key,w in [('cash',b_cash),('spy_buy_hold',b_spy),('sixty_forty',b_60),('equal_weight',b_eq)]:
            plan={0:w} if key in ('cash','spy_buy_hold') else {j:w for j in range(0,len(xx),s['step'])};sim=ledger(xx,rr,dates,plan,all_caps,capital=capital,cost_bps=cost,delay=delay);ref_returns[key]=sim['returns'];reference[key]=summarize(sim,rr,sim['returns']);reference[key]['locked']=metrics(sim['returns'][lock:],rr[lock:])
        bench=ref_returns['spy_buy_hold'];results={};selected_detail=None;boot={};development={}
        for key in model_keys:
            if failures[key]:results[key]={'status':'unavailable','reason':failures[key][0]['reason'],'failed_folds':failures[key],'available_folds':len(plans[key])};continue
            sim=strategy_ledger(key,xx,rr,dates,plans[key],uu,capital=capital,cost_bps=cost,delay=delay,turnover_limit=turn)
            if sim['status']!='computed':results[key]=sim;continue
            v=summarize(sim,rr,bench);ret=sim['returns'];v['locked']=metrics(ret[lock:],rr[lock:]);v['development']=metrics(ret[:lock],rr[:lock]) if lock>=2 else None;v['locked_active']=summarize({'status':'computed','returns':ret[lock:],'total_cost':0.,'annual_turnover':0.,'final_nav':0.},rr[lock:],bench[lock:])['active'];boot[key]=ret[lock:];development[key]=ret[:lock]
            shock=strategy_ledger(key,xx,rr,dates,plans[key],uu,capital=capital,cost_bps=min(400,cost*2),delay=delay,turnover_limit=turn,borrow_bps=600.,funding_bps=400.);late=strategy_ledger(key,xx,rr,dates,plans[key],uu,capital=capital,cost_bps=cost,delay=min(3,delay+1),turnover_limit=turn);gross=strategy_ledger(key,xx,rr,dates,plans[key],uu,capital=capital,cost_bps=0,delay=delay,turnover_limit=turn,borrow_bps=0.,funding_bps=0.);v['sensitivity']={'double_cost_locked_cagr':metrics(shock['returns'][lock:],rr[lock:])['cagr'] if shock['status']=='computed' else None,'extra_delay_locked_cagr':metrics(late['returns'][lock:],rr[lock:])['cagr'] if late['status']=='computed' else None,'zero_cost_locked_cagr':metrics(gross['returns'][lock:],rr[lock:])['cagr'] if gross['status']=='computed' else None};v['fold_metrics']=[]
            for f in ff:
                a,b=f.decision-first,f.test_end-first;v['fold_metrics'].append({'phase':f.phase,'start':str(dates[a][0]),'end':str(dates[b-1][1]),'cumulative':float(np.prod(1+ret[a:b])-1),'months':b-a})
            v['stress_subperiods']={}
            for label,start,end in [('gfc_2008',date(2008,1,1),date(2008,12,31)),('covid_2020',date(2020,2,1),date(2020,3,31)),('rate_shock_2022',date(2022,1,1),date(2022,12,31))]:
                ix=[i for i,(a,b) in enumerate(dates) if start<=b<=end];expected=(end.year-start.year)*12+end.month-start.month+1;v['stress_subperiods'][label]={'status':'computed','cumulative':float(np.prod(1+ret[ix])-1),'benchmark_cumulative':float(np.prod(1+bench[ix])-1)} if len(ix)==expected else {'status':'unavailable','reason':'Full stress window not covered'}
            if key==s['selected']:
                capacity=strategy_ledger(key,xx,rr,dates,plans[key],uu,capital=capital,cost_bps=cost,delay=delay,turnover_limit=turn,max_trade_notional=.25*capital);selected_detail={'model':key,'ledger':sim['ledger'],'trades':sim['trades'],'capacity_scenario':{'max_trade_notional':.25*capital,'status':capacity['status'],'reason':capacity.get('reason')},'ids':[{'id':a['id'],'ticker':a['ticker']} for a in assets]}
            results[key]=v
        deployed={'status':'unavailable','reason':'No locked selection or at least one final fold failed'}
        if locked_model and not any(f['phase']=='locked_holdout' for f in failures[locked_model]):
            p={j-lock:w for j,w in plans[locked_model].items() if j>=lock};sim=strategy_ledger(locked_model,xx[lock:],rr[lock:],dates[lock:],p,uu[lock:],capital=capital,cost_bps=cost,delay=delay,turnover_limit=turn);fresh=ledger(xx[lock:],rr[lock:],dates[lock:],{0:b_spy},all_caps[lock:],capital=capital,cost_bps=cost,delay=delay);deployed=summarize(sim,rr[lock:],fresh['returns']);deployed['fresh_spy']=metrics(fresh['returns'],rr[lock:]);deployed['model']=locked_model
        dates_iso=[str(b) for a,b in dates];fingerprint=hashlib.sha256(x.tobytes()+rf.tobytes()+upper.tobytes()).hexdigest();return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'matrix_hash':fingerprint,'configuration':s,'currency':currency,'scope':scope,'asset_count':k,'observations':n,'first':str(dates[0][0]),'last':dates_iso[-1],'development_months':lock,'locked_test_months':len(xx)-lock,'locked_start':str(intervals[hold][0]),'dates':dates_iso,'folds':fold_rows,'registry':REGISTRY,'strategies':results,'benchmarks':reference,'locked_selection':{'model':locked_model,'validation_scores':locked_selection,'frozen_parameters':locked_params,'fresh_deployment':deployed},'multiple_testing':bootstrap_comparison(boot,bench[lock:],seed=seed),'selected_detail':selected_detail,'unsupported':UNSUPPORTED,'unverified_mandate_constraints':unknown,'warning':'Research only. Current endpoint cohort is retrospective; dated historical membership restricts purchases/exits, but delisted/excluded securities and exact publication times not reconstructed. Total-return monthly accounts reinvest distributions; no actual quotes/shares/ADV/tax. CHF BIL cash proxy not native risk-free. Parameter selection frozen before final holdout; later folds refit past information, no test-based tuning. Repeat configuration exploration can contaminate holdout.'}


def cached_report(root,data):
    s=settings(data);root=Path(root);mandate=data.get('mandate')
    if mandate is not None:return run(root,s,mandate)
    d=date.fromisoformat(s['as_of']);r=returns_report(root,d);f=batch_report(root,d);fac=factor_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),fac.get('run_id'),s],sort_keys=True).encode()).hexdigest();folder=root/'data/processed/walk_forward';folder.mkdir(parents=True,exist_ok=True);path=folder/f'{key}.json'
    try:
        result=json.loads(path.read_text())
        if result.get('run_id')==key and result.get('version')==VERSION:return result
    except (OSError,ValueError):pass
    try:result=run(root,s)|{'run_id':key,'created_at_utc':datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        # Public research configurations only; no private mandate persisted.
        failure={'run_id':key,'configuration':s,'status':'failed','reason':str(exc),'created_at_utc':datetime.now(timezone.utc).isoformat()};p=folder/f'{key}-failed.json'
        with tempfile.NamedTemporaryFile(mode='w',dir=folder,delete=False) as out:json.dump(failure,out,allow_nan=False);tmp=Path(out.name)
        tmp.replace(p);raise
    with tempfile.NamedTemporaryFile(mode='w',dir=folder,delete=False) as out:json.dump(result,out,allow_nan=False);tmp=Path(out.name)
    tmp.replace(path);return result
