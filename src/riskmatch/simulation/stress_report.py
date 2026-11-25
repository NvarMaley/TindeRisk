"""Current research targets, historical windows and conditional forward projections."""
from datetime import date,datetime,timezone
from pathlib import Path
import json,hashlib,tempfile
import numpy as np
import duckdb
from threadpoolctl import threadpool_limits
from riskmatch.simulation.stress_mc import VERSION,MODELS,paths,project,covariance_model
from riskmatch.optimization.mean_variance_report import aligned,config,category
from riskmatch.backtesting.walk_models import REGISTRY,fit_models,SIGNED
from riskmatch.strategies.long_only_report import load_signals,verified_pit
from riskmatch.strategies.alternative_report import macro_signals
from riskmatch.profiling.mandate import validate_mandate,add_month
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.analytics.factor_report import factor_report

SCENARIOS={
 'equity_crash':(-.35,-.005,-.005,0.,0.,-.25),
 'recession':(-.20,-.015,-.010,0.,0.,-.20),
 'inflation_shock':(-.15,.02,.0075,.02,0.,.15),
 'rates_up_200bp':(-.08,.02,.02,0.,0.,0.),
 'steepening':(-.05,-.005,.01,0.,0.,0.),
 'flattening':(-.05,.01,-.005,0.,0.,0.),
 'real_yields_up_200bp':(-.08,0.,.02,0.,0.,-.10),
 'equity_bond_joint_crash':(-.30,.025,.02,0.,0.,-.15),
 'chf_appreciation':(0.,0.,0.,0.,-.10,0.),
 'margin_liquidity_shock':(-.20,.01,.01,0.,-.05,-.20),
}
HISTORICAL={'dot_com_2000_2002':(date(2000,1,1),date(2002,12,31),36),'gfc_2008':(date(2008,1,1),date(2008,12,31),12),'covid_2020':(date(2020,2,1),date(2020,3,31),2),'rate_shock_2022':(date(2022,1,1),date(2022,12,31),12)}
DURATION={'BIL':.10,'SHY':1.9,'IEF':7.5,'TLT':16.,'TIP':6.5}


def scenario_matrix(assets,x,currency):
    spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY');b=x[:,spy];beta=(x-x.mean(0)).T@(b-b.mean())/((len(b)-1)*max(np.var(b,ddof=1),1e-12));out={};details={}
    for key,(eq,nominal,real,infl,fx,commodity) in SCENARIOS.items():
        r=np.zeros(len(assets)+1)
        for i,a in enumerate(assets):
            k=category(a);ticker=a['ticker']
            if k in ('equity','reit'):r[i]=eq*np.clip(beta[i],0,2)+( -.02 if k=='reit' and nominal>0 else 0.)
            elif k=='treasury':
                d=DURATION.get(ticker,5.);dy=real if ticker=='TIP' else nominal
                if key in ('steepening','flattening'):dy=nominal+(real-nominal)*min(d/16,1)
                r[i]=-d*dy+.5*d*(d+1)*dy*dy+(infl if ticker=='TIP' else 0.)
            elif k=='commodity_etp':r[i]=commodity+(infl if ticker in ('GLD','SLV') else 0.)
            else:r[i]=0.
        if currency=='CHF':r=(1+r)*(1+fx)-1
        out[key]=np.maximum(r,-1.);details[key]={'market_equity_shock':eq,'nominal_rate_shift':nominal,'real_long_rate_shift':real,'tips_indexation':infl,'chf_fx_shock':fx if currency=='CHF' else 0.,'commodity_shock':commodity,'liquidity_haircut_assumption':.02 if key=='margin_liquidity_shock' else 0.}
    return out,details


def schedule(s,mandate=None):
    start=date.fromisoformat(s['as_of']);end=add_month(start,s['months']);events={};goals={};bounds=[start]
    if mandate:
        report=validate_mandate(mandate)
        if report['conflicts'] or mandate['currency']!=s['currency'] or mandate['as_of']!=s['as_of']:raise ValueError('Mandate conflicts or valuation date/currency mismatch')
        end=date.fromisoformat(mandate['horizon_date']);capital=float(mandate['capital']);infl=float(mandate['inflation']) if mandate['inflation'] is not None else s['inflation']
        if end>add_month(start,240):raise ValueError('Monte Carlo mandate horizon exceeds 20 years')
        raw=[(date.fromisoformat(v['date']),v['kind'],float(v['amount'])) for v in mandate['dated_flows']];contrib=float(mandate['contribution_monthly']);withdraw=float(mandate['withdrawal_monthly']);gg=[{'index':g['goal_index'],'date':g['due_date'],'target':g['target_nominal_base'] if g['objective_id']!='OBJ02' else None,'funding':g['funding'],'priority':g['priority']} for g in report['goals']]
    else:
        capital=s['capital'];infl=s['inflation'];raw=[];contrib=s['contribution'];withdraw=s['withdrawal'];gg=[{'index':0,'date':str(end),'target':s['target']*(1+infl)**(s['months']/12) if s['target_real'] else s['target'],'funding':False,'priority':1}]
    m=1
    while bounds[-1]<end:bounds.append(min(add_month(start,m),end));m+=1
    fractions=[]
    for i,(a,b) in enumerate(zip(bounds,bounds[1:])):
        full=add_month(start,i+1);days=(full-a).days;fractions.append((b-a).days/days)
        if b==full:
            if contrib:events.setdefault(i,[]).append((1.,'contribution',contrib))
            if withdraw:events.setdefault(i,[]).append((1.,'withdrawal',withdraw))
        for d,k,v in raw:
            if a<d<=b:events.setdefault(i,[]).append(((d-a).days/days,k,v))
        for g in gg:
            d=date.fromisoformat(g['date'])
            if a<d<=b:goals.setdefault(i,[]).append(((d-a).days/days,g))
    return capital,infl,bounds,events,goals,np.array(fractions)


def settings(data):
    scope=data.get('scope','core');s={'as_of':data['as_of'],'scope':scope,'currency':data.get('currency','USD'),'selected':data.get('selected','mean_variance_utility'),'capital':data.get('capital',100000.),'months':data.get('months',60),'paths':data.get('paths',1000),'seed':data.get('seed',24),'contribution':data.get('contribution',500.),'withdrawal':data.get('withdrawal',0.),'inflation':data.get('inflation',.02),'target':data.get('target',150000.),'target_real':data.get('target_real',False),'cost_bps':data.get('cost_bps',10.),'frequency':data.get('frequency',3),'max_weight':data.get('max_weight',.65 if scope=='core' else .05),'optimizer_limit':data.get('optimizer_limit',64),'include_instrument_examples':data.get('include_instrument_examples',True)}
    if date.fromisoformat(s['as_of'])>date.today() or scope not in ('core','cohort') or s['currency'] not in ('USD','CHF') or s['selected'] not in (*REGISTRY,'spy','sixty_forty','cash') or not isinstance(s['target_real'],bool) or not isinstance(s['include_instrument_examples'],bool):raise ValueError('Invalid scenario request')
    for k,lo,hi in [('months',1,240),('paths',100,2000),('seed',0,2**31-1),('frequency',1,12),('optimizer_limit',32,128)]:
        v=s[k]
        if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:raise ValueError('Invalid integer: '+k)
    for k,lo,hi in [('capital',1,1e9),('contribution',0,1e7),('withdrawal',0,1e7),('target',1,1e10),('inflation',-.1,.30),('cost_bps',0,200),('max_weight',.001,1)]:
        v=s[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid value: '+k)
        s[k]=float(v)
    return s


def standalone_instruments(root,as_of,capital):
    from riskmatch.analytics.treasury_report import run_report
    from riskmatch.analytics.futures_report import verified,parse_source
    import csv
    out={}
    try:
        r=run_report(root,{'as_of':str(as_of)});rows=[b for b in r['bonds'] if b['status']=='computed'];groups={}
        for b in rows:
            v=b['yield_shocks']['200'];groups.setdefault(b['type'],[]).append(v)
        out['treasuries']={'status':'conditional','date':r['valuation_date'],'covered':len(rows),'shock_200bp_by_type':{k:{'count':len(v),'median_price_change':float(np.median(v)),'worst':float(min(v))} for k,v in groups.items()},'warning':'Exact YTM repricing +200bp for individual nominal/real securities at government marks assumed clean; TIPS index ratio held fixed, floor excluded. Not in common portfolio.'}
    except (ValueError,KeyError,OSError) as e:out['treasuries']={'status':'unavailable','reason':str(e)}
    try:
        base=Path(root)/'data/raw/research_futures';receipts=[]
        for p in base.glob('*/receipt-*.json'):
            r=json.loads(p.read_text());stamp=datetime.fromisoformat(r['acquired_at_utc']).date()
            if stamp<=as_of:receipts.append((stamp,p,r))
        _,p,r=max(receipts,key=lambda v:(v[0],str(v[1])));specs={q['root']:q for q in csv.DictReader((Path(root)/'configs/futures_reference_specs.csv').open())};out_rows=[]
        for q in r['rows']:
            file=verified(p.parent,q['file']);stat=file.stat();marks,_=parse_source(str(file),stat.st_mtime_ns,stat.st_size);mark=marks[-1];mult=float(specs[q['root']]['usd_per_price_unit']);notional=abs(mark.price)*mult;pnl=-.20*notional;post=capital+pnl;stressed=.20*notional;out_rows.append({'root':q['root'],'date':str(mark.stamp.date()),'notional':notional,'one_long_contract_pnl':pnl,'stressed_margin':stressed,'margin_shortfall':max(0.,stressed-post)})
        out['futures']={'status':'archived_only','rows':out_rows,'warning':'One long archived contract, adverse 20% price move, margin doubled from 10% to 20% of notional; starting illustrative capital. No current quote or clearing schedule.'}
    except (ValueError,KeyError,OSError) as e:out['futures']={'status':'unavailable','reason':str(e)}
    return out


def run(root,s,mandate=None):
    as_of=date.fromisoformat(s['as_of']);capital,infl,bounds,events,goals,fractions=schedule(s,mandate);months=len(bounds)-1;count=s['paths'];seed=s['seed'];currency=s['currency']
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,s['scope']);n=len(assets);day=intervals[-1][1];u,unknown=config(assets,s['max_weight'],0.,mandate)[0].upper,config(assets,s['max_weight'],0.,mandate)[1];stock=np.array([a['source']=='stock_monthly' for a in assets]);signals=load_signals(root,as_of,assets,[day],version);membership=signals[0];caps={}
        if stock.any():
            u[stock]=[u[i] if str(assets[i]['instrument']) in membership.get(day,set()) else 0. for i in np.flatnonzero(stock)];p=verified_pit(root,version)
            with duckdb.connect() as db:caps=dict(db.execute('select instrument,market_cap_source_units from read_parquet(?) where observation_date=? and market_cap_source_units>0',[str(p/'stock_membership.parquet'),day]).fetchall())
        macro=macro_signals(root,version,[day]);models=fit_models(list(REGISTRY),x[-60:],rf[-60:],assets,u,day,signals,optimizer_limit=s['optimizer_limit'],market_caps=caps,seed=seed,macro=macro.get(day));spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY');ief=next(i for i,a in enumerate(assets) if a['ticker']=='IEF');sp=np.zeros(n);sp[spy]=1;balanced=sp*.6;balanced[ief]=.4
        for key,w in [('spy',sp),('sixty_forty',balanced),('cash',np.zeros(n))]:models[key]={'status':'computed','weights':w,'candidate_count':n,'external_reference':True}
        if mandate:
            for k in SIGNED:models[k]={'status':'unavailable','reason':'Signed positions cannot certify client permissions, borrow, collateral and gross/net limits'}
        matrix,scenario_specs=scenario_matrix(assets,x,currency);comparison={};valid={};hist=np.c_[x,rf]
        for key,v in models.items():
            if v['status']!='computed':comparison[key]=v;continue
            w=np.asarray(v['weights']);full=np.r_[w,1-w.sum()];shocks={};historical={}
            for name,z in matrix.items():
                ret=float(full@z);haircut=.02*np.abs(w).sum() if name=='margin_liquidity_shock' else 0.;post=float(capital*(1+ret-haircut));marked=capital*w*(1+z[:-1]);postcash=capital*full[-1]*(1+z[-1])-capital*haircut;free=postcash+np.minimum(marked,0).sum();gross=float(np.abs(marked).sum()/post) if post>0 else None;shocks[name]={'return':ret-haircut,'loss_amount':float(-capital*(ret-haircut)),'post_shock_nav':post,'assumed_liquidity_cost':capital*haircut,'free_cash_after_short_collateral':float(free),'gross_after_shock':gross,'insolvency_shortfall':max(0.,-post)}
            for name,(start,end,expected) in HISTORICAL.items():
                ix=[i for i,(a,b) in enumerate(intervals) if start<=b<=end];r=hist[ix]@full;historical[name]={'status':'computed','cumulative':float(np.prod(1+r)-1)} if len(ix)==expected and np.all(r>=-1) else {'status':'unavailable','reason':'Complete historical window not covered or signed account exhausted'}
            comparison[key]={'status':'computed','candidate_count':v.get('candidate_count'),'signed':bool((w<0).any()),'scenarios':shocks,'historical':historical,'annual_mean':float((hist@full).mean()*12),'annual_volatility':float((hist@full).std(ddof=1)*np.sqrt(12)),'worst_shock':min(shocks,key=lambda k:shocks[k]['return']),'external_reference':v.get('external_reference',False)};valid[key]=w
        # Shared joint *portfolio-return* Gaussian comparison, zero cost and constant weights.
        keys=list(valid);full=np.array([np.r_[valid[k],1-valid[k].sum()] for k in keys]);cashref=np.zeros(n+1);cashref[-1]=1;projection=np.r_[full,cashref[None,:]];mu,fac,noise,_=covariance_model(hist);pf=fac@projection.T;diag=(projection*(noise**2))@projection.T;ev,vec=np.linalg.eigh(diag);root_noise=np.sqrt(np.maximum(ev,0))[:,None]*vec.T;rng=np.random.default_rng(seed);streams=[]
        for _ in range(months):streams.append(np.maximum(projection@mu+rng.standard_normal((count,len(pf)))@pf+rng.standard_normal((count,len(projection)))@root_noise,-.999999))
        cube=np.stack(streams,axis=1)
        for j,key in enumerate(keys):
            # Aggregate gross constant-weight return; no per-asset turnover or borrow claim.
            g=((np.c_[cube[:,i,j],cube[:,i,-1]],0) for i in range(months));v=project(g,np.array([1.]),capital,months,count,events,goals,inflation=infl,cost_bps=0,frequency=12,fractions=fractions);comparison[key]['gross_normal_comparison']={'percentiles':v['percentiles'],'goals':v['goals'],'expected_unmet_cash':v['expected_unmet_cash'],'all_targeted_goals_probability':v['all_targeted_goals_probability']}
        key=s['selected'];detail=None
        if key in valid:
            w=valid[key];active=np.flatnonzero(abs(w)>1e-8);h=np.c_[x[:,active],rf];weights=w[active];market=x[:,spy];work=count*months*max(1,len(active));detail={'model':key,'positions':[{'id':assets[i]['id'],'ticker':assets[i]['ticker'],'weight':float(w[i])} for i in active],'cash_weight':float(1-w.sum()),'models':{},'sensitivities':{},'active_assets':len(active)}
            if work>30000000:detail['reason']='Detailed workload exceeds 30 million asset/path/month cells; reduce paths or horizon'
            else:
                def sim(model,**kw):
                    shock_infl=kw.pop('inflation',infl);cost=kw.pop('cost_bps',s['cost_bps']);zero_excess=kw.pop('zero_excess',False);ev=events;gs=goals;fr=fractions;calibration=h.copy()
                    if zero_excess:calibration[:,:-1]+=h[:,-1].mean()-h[:,:-1].mean(0);calibration=np.maximum(calibration,-.999999)
                    if shock_infl!=infl:
                        if mandate:_,_,_,ev,gs,fr=schedule(s,mandate|{'inflation':shock_infl})
                        else:_,_,_,ev,gs,fr=schedule(s|{'inflation':shock_infl})
                    return project(paths(calibration,months,count,model,seed=seed,market=market,**kw),weights,capital,months,count,ev,gs,inflation=shock_infl,cost_bps=cost,frequency=s['frequency'],fractions=fr)
                for model in MODELS:detail['models'][model]=sim(model)
                for name,model,kw in [('lower_mean','normal',{'mean_shift':-.03}),('zero_expected_excess','normal',{'zero_excess':True}),('higher_volatility','normal',{'vol_scale':1.5}),('inflation_plus_2pp','normal',{'inflation':min(.5,infl+.02)}),('double_costs','normal',{'cost_bps':min(200,s['cost_bps']*2)}),('more_stress_regimes','regime',{'regime_stress':2.})]:
                    v=sim(model,**kw);detail['sensitivities'][name]={k:v[k] for k in ('percentiles','real_percentiles','goals','expected_unmet_cash','mean_fees','insolvency_probability')}
                # Convergence: same calibration, half paths with separate seeded estimate.
                half=max(50,count//2);v=project(paths(h,months,half,'normal',seed=seed,market=market),weights,capital,months,half,events,goals,inflation=infl,cost_bps=s['cost_bps'],frequency=s['frequency'],fractions=fractions);detail['convergence']={'half_paths':half,'half_median':v['percentiles'][2],'full_median':detail['models']['normal']['percentiles'][2]}
                m,_,_,cov=covariance_model(h);detail['calibration']={'mean_monthly':m.tolist(),'covariance_psd':bool(np.linalg.eigvalsh(cov).min()>=-1e-10),'history_months':len(h),'df_student_t':5,'bootstrap_block_months':6}
        instruments=standalone_instruments(root,as_of,capital) if s['include_instrument_examples'] else {}
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'configuration':s,'capital':capital,'horizon_months':months,'dates':[str(d) for d in bounds],'inflation':infl,'currency':currency,'asset_count':n,'history_months':len(x),'history_first':str(intervals[0][0]),'history_last':str(day),'scenario_specs':scenario_specs,'comparison':comparison,'selected_detail':detail,'instrument_examples':instruments,'unverified_mandate_constraints':unknown,'warning':'Conditional research distributions, not predictions. Retrospective endpoint cohort, current historical fit (not OOS validation). Gross constant-weight Gaussian comparison is distinct from selected asset-level fee/flow/borrow/quarterly rebalance projection. Historical and hypothetical scenarios are separate; individual Treasuries and archived futures not in common portfolios. USD reference RF; CHF unhedged BIL proxy, no hedge certification. No actual tax, ADV, clearing margin, or suitability.'}


def cached_report(root,data):
    s=settings(data);root=Path(root);mandate=data.get('mandate')
    if mandate:return run(root,s,mandate)
    d=date.fromisoformat(s['as_of']);r=returns_report(root,d);f=batch_report(root,d);fac=factor_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),fac.get('run_id'),s],sort_keys=True).encode()).hexdigest();folder=root/'data/processed/stress_mc';folder.mkdir(parents=True,exist_ok=True);path=folder/f'{key}.json'
    try:
        out=json.loads(path.read_text())
        if out.get('run_id')==key and out.get('version')==VERSION:return out
    except (OSError,ValueError):pass
    out=run(root,s)|{'run_id':key,'created_at_utc':datetime.now(timezone.utc).isoformat()}
    with tempfile.NamedTemporaryFile(mode='w',dir=folder,delete=False) as f:json.dump(out,f,allow_nan=False);tmp=Path(f.name)
    tmp.replace(path);return out
