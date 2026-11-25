"""Chronological signal-based strategies on the common retrospective research cohort."""
from datetime import date
from pathlib import Path
import hashlib,json,tempfile
import numpy as np
import duckdb
from threadpoolctl import threadpool_limits
from riskmatch.strategies.long_only import VERSION,REGISTRY,FACTORS,allocate,ranked,alpha_signal,dynamic_ledger
from riskmatch.optimization.mean_variance_report import aligned,config
from riskmatch.analytics.factor_report import factor_report
from riskmatch.market_data.returns import returns_report
from riskmatch.analytics.forecast_batch import batch_report
from riskmatch.backtesting.baselines import metrics
from riskmatch.optimization.downside import stats


def verified_pit(root,version):
    base=Path(root)/'data/processed/pit';r=json.loads((base/'report.json').read_text());ret=json.loads((Path(root)/'data/processed/returns/report.json').read_text())
    if ret['return_id']!=version or ret['snapshot_id']!=r['snapshot_id']:raise ValueError('PIT identity mismatch')
    folder=base/r['snapshot_id']
    for name in ('stock_membership','ccm_links','fundamentals_annual'):
        e=next(x for x in r['datasets'] if x['dataset']==name)
        with (folder/(name+'.parquet')).open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=e['file_hash']:raise ValueError('PIT input hash mismatch')
    return folder


def load_signals(root,as_of,assets,dates,version):
    stock=[str(a['instrument']) for a in assets if a['source']=='stock_monthly'];membership={};scores={};books={}
    if not stock:return membership,scores,books
    pit=verified_pit(root,version);fr=factor_report(root,as_of)
    if fr['status']!='complete':raise ValueError('Dated factor score report unavailable')
    fp=Path(root)/'data/processed/factors'/fr['run_id']/'scores.parquet'
    with duckdb.connect(config={'threads':4}) as db:
        db.execute('CREATE TEMP TABLE wanted_dates(d DATE)');db.executemany('INSERT INTO wanted_dates VALUES (?)',[(d,) for d in dates]);db.execute('CREATE TEMP TABLE wanted_ids(instrument VARCHAR)');db.executemany('INSERT INTO wanted_ids VALUES (?)',[(i,) for i in stock]);
        rows=db.execute('SELECT instrument,observation_date FROM read_parquet(?) WHERE instrument IN (SELECT instrument FROM wanted_ids) AND observation_date IN (SELECT d FROM wanted_dates)',[str(pit/'stock_membership.parquet')]).fetchall()
        for i,d in rows:membership.setdefault(d,set()).add(str(i))
        fields=','.join(k+'_score' for k in FACTORS)
        rows=db.execute(f'SELECT instrument,CAST(ranking_date AS DATE),{fields} FROM read_parquet(?) WHERE instrument IN (SELECT instrument FROM wanted_ids) AND CAST(ranking_date AS DATE) IN (SELECT d FROM wanted_dates)',[str(fp)]).fetchall()
        for i,d,*v in rows:scores[(str(i),d)]=np.array([float(z) if z is not None else np.nan for z in v])
        # Join original accepted filing at the same dated score's fiscal and accepted dates.
        rows=db.execute("""WITH s AS (SELECT instrument,CAST(ranking_date AS DATE) d,accepted,fiscal_date FROM read_parquet(?) WHERE instrument IN (SELECT instrument FROM wanted_ids) AND CAST(ranking_date AS DATE) IN (SELECT d FROM wanted_dates) AND accepted IS NOT NULL AND CAST(accepted AS DATE)<CAST(ranking_date AS DATE) AND date_diff('day',CAST(fiscal_date AS DATE),CAST(ranking_date AS DATE)) BETWEEN 0 AND 1095),
          links AS (SELECT s.instrument,s.d,s.accepted,s.fiscal_date,min(l.instrument) gvkey FROM s JOIN read_parquet(?) l ON s.instrument=l.LPERMNO AND s.d>=l.observation_date AND (l.valid_until_inclusive IS NULL OR s.d<=l.valid_until_inclusive) WHERE l.LINKTYPE IN ('LC','LU') AND l.LINKPRIM IN ('P','C') GROUP BY 1,2,3,4 HAVING count(DISTINCT l.instrument)=1)
          SELECT l.instrument,l.d,min(f.value) book FROM links l JOIN read_parquet(?) f ON f.instrument=l.gvkey AND CAST(f.observation_date AS DATE)=CAST(l.fiscal_date AS DATE) AND f.accepted=l.accepted WHERE f.tag='StockholdersEquity' AND f.qtrs=0 AND f.uom='USD' GROUP BY 1,2 HAVING count(DISTINCT f.value)=1 AND min(f.value)>0""",[str(fp),str(pit/'ccm_links.parquet'),str(pit/'fundamentals_annual.parquet')]).fetchall()
        for i,d,v in rows:books[(str(i),d)]=float(v)
    return membership,scores,books


def weights_at(key,history,assets,upper,day,membership,scores,books,core_budget,spy):
    n=len(assets);ids=[a['id'] for a in assets];stock=np.array([a['source']=='stock_monthly' for a in assets]);etf=~stock;u=upper.copy();u[stock]=[upper[i] if str(assets[i]['instrument']) in membership.get(day,set()) else 0. for i in np.flatnonzero(stock)];rationale={'as_of':str(day),'eligible_assets':int((u>0).sum())};
    if u.sum()<1-1e-10:return None,u,rationale|{'reason':'Insufficient dated eligible capacity'}
    signals=np.array([scores.get((str(a['instrument']),day),np.full(len(FACTORS),np.nan)) if stock[i] else np.full(len(FACTORS),np.nan) for i,a in enumerate(assets)]);book=np.array([books.get((str(a['instrument']),day),np.nan) if stock[i] else np.nan for i,a in enumerate(assets)]);alpha=alpha_signal(history[-36:],history[-36:,spy]);
    def active():return ranked(alpha,u,ids,.2,positive_only=True)
    def one_factor(k):return ranked(signals[:,FACTORS.index(k)],u,ids,.3,fallback=False)
    try:
        if key=='passive_index':
            if u[spy]<1-1e-9:raise ValueError('Single ETF replication violates asset cap or eligibility')
            w=np.zeros(n);w[spy]=1
        elif key=='passive_etfs':w=allocate(etf.astype(float),u)
        elif key=='active_long_only':w,m=active();rationale|=m
        elif key=='smart_beta_equal':w=allocate((u>0).astype(float),u)
        elif key=='smart_beta_factor':
            count=np.isfinite(signals).sum(1);s=np.divide(np.nansum(signals,axis=1),count,out=np.full(n,np.nan),where=count>=3);w,m=ranked(s,u,ids,.3,fallback=False);rationale|=m
        elif key=='smart_beta_fundamental':
            w=allocate(np.where(np.isfinite(book),book,0),u);rationale['positive_book_coverage']=int(np.sum(np.isfinite(book)&(u>0)))
        elif key=='factor_investing':
            parts=[]
            for f in FACTORS:parts.append(one_factor(f)[0])
            w=np.mean(parts,axis=0);rationale['sleeve_count']=len(parts)
        elif key.startswith('factor_'):w,m=one_factor(key[7:]);rationale|=m
        elif key=='core_satellite':
            core=allocate(etf.astype(float),u) if core_budget>0 else np.zeros(n);sat,m=active() if core_budget<1 else (np.zeros(n),{});w=core_budget*core+(1-core_budget)*sat;rationale|={'core_budget':core_budget,'satellite_budget':1-core_budget,**m}
        else:raise ValueError('Unknown strategy')
        return w,u,rationale
    except ValueError as e:return None,u,rationale|{'reason':str(e)}


def risk_matched(history,weights,spy,bil):
    h=np.asarray(history)[-36:];vol=float(np.std(h@weights,ddof=1));a=h[:,spy];b=h[:,bil];grid=np.linspace(0,1,1001);v=np.std(b[:,None]+(a-b)[:,None]*grid[None,:],axis=0,ddof=1);i=int(np.argmin(abs(v-vol)));w=np.zeros(h.shape[1]);w[spy]=grid[i];w[bil]=1-grid[i];return w,float(abs(v[i]-vol)*np.sqrt(12))


def summarize(ledger,rf,benchmark):
    if ledger['status']!='computed':return ledger
    r=ledger['returns'];return {'status':'computed','net':metrics(r,rf),'active':{k:v for k,v in stats(r,benchmark=benchmark).items() if k in ('tracking_error','information_ratio','active_annual_mean')},'fees':ledger['fees'],'annual_turnover':ledger['annual_turnover'],'ledger':ledger['ledger'],'nav':np.cumprod(1+r).tolist()}


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);scope=data.get('scope','cohort');currency=data.get('currency','USD');cap=data.get('max_weight',.05 if scope=='cohort' else .65);cost=data.get('cost_bps',10.);turn=data.get('turnover_limit',.35);frequency=data.get('frequency','monthly');core_budget=data.get('core_budget',.6);mandate=data.get('mandate')
    if as_of>date.today() or scope not in ('cohort','core') or currency not in ('USD','CHF') or frequency not in ('monthly','quarterly') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in (cap,cost,turn,core_budget)) or not 0<cap<=1 or not 0<=cost<=200 or not 0<=turn<=1 or not 0<=core_budget<=1:raise ValueError('Invalid strategy settings')
    if mandate and mandate['currency']!=currency:raise ValueError('Mandate currency mismatch')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);c,unknown=config(assets,cap,0.,mandate);u=c.upper;n=len(assets);cut=int(.8*len(x));dates=intervals[cut:];test=x[cut:];origins=[a for a,b in dates]+[intervals[-1][1]];membership,scores,books=load_signals(root,as_of,assets,origins,version);spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY' and a['source']=='etf_crsp_monthly');bil=next(i for i,a in enumerate(assets) if a['ticker']=='BIL' and a['source']=='etf_crsp_monthly');benchmark=test[:,spy];bw=np.zeros(n);bw[spy]=1;bench=dynamic_ledger(test,dates,[bw]*len(test),[np.ones(n)]*len(test),cost,1.,frequency)
        rows={};current={};score_coverage=[]
        for key in REGISTRY:
            targets=[];caps=[];rationale=[]
            for j,day in enumerate(origins[:-1]):
                w,cu,r=weights_at(key,x[:cut+j],assets,u,day,membership,scores,books,core_budget,spy);targets.append(w);caps.append(cu);rationale.append(r)
            w,cu,r=weights_at(key,x,assets,u,origins[-1],membership,scores,books,core_budget,spy);current[key]={'status':'target_available' if w is not None else 'unavailable','rationale':r,'holdings':[] if w is None else [{'id':a['id'],'ticker':a['ticker'],'weight':float(w[i])} for i,a in enumerate(assets) if w[i]>1e-8]}
            if any(t is None for t in targets):rows[key]={'status':'unavailable','reason':next(r.get('reason','Unknown') for t,r in zip(targets,rationale) if t is None),'target_coverage':sum(t is not None for t in targets),'rationale':rationale};continue
            ledger=dynamic_ledger(test,dates,targets,caps,cost,turn,frequency);result=summarize(ledger,rf[cut:],benchmark);result['rationale']=rationale
            if ledger['status']=='computed':
                gross=dynamic_ledger(test,dates,targets,caps,0.,turn,frequency);high=dynamic_ledger(test,dates,targets,caps,min(200,max(25,cost*2)),turn,frequency);result['gross']=metrics(gross['returns'],rf[cut:]) if gross['status']=='computed' else None;result['cost_shock_cagr']=metrics(high['returns'],rf[cut:])['cagr'] if high['status']=='computed' else None
                matched=[risk_matched(x[:cut+j],w,spy,bil) for j,w in enumerate(ledger['weights'])];rm=dynamic_ledger(test,dates,[m[0] for m in matched],[np.ones(n)]*len(test),cost,1.,frequency);result['risk_matched_reference']=summarize(rm,rf[cut:],benchmark);result['risk_match_mean_annual_vol_gap']=float(np.mean([m[1] for m in matched]));result['last_executed_weights']=[{'id':a['id'],'ticker':a['ticker'],'weight':float(ledger['weights'][-1,i])} for i,a in enumerate(assets) if ledger['weights'][-1,i]>1e-8]
            rows[key]=result
        return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'as_of':str(as_of),'scope':scope,'currency':currency,'asset_count':n,'observations':len(x),'train_months':cut,'test_months':len(test),'first':str(dates[0][0]),'last':str(dates[-1][1]),'configuration':{'max_weight':cap,'cost_bps':cost,'turnover_limit':turn,'frequency':frequency,'core_budget':core_budget},'registry':REGISTRY,'strategies':rows,'current_targets':current,'benchmark':summarize(bench,rf[cut:],benchmark),'membership_dates':len(membership),'factor_score_rows':len(scores),'fundamental_rows':len(books),'reference_is_cash_proxy':currency=='CHF','unverified_mandate_constraints':unknown,'warning':'Static endpoint cohort with dated historical top-1000 eligibility, not historical index membership. Target formation uses previous closes only; hypothetical close fills. External SPY and risk-matched references exempt from candidate cap. No suitability/actual execution certification.'}


def cached_report(root,data):
    if data.get('mandate') is not None:return run_report(root,data)
    root=Path(root);scope=data.get('scope','cohort');s={'as_of':data['as_of'],'scope':scope,'currency':data.get('currency','USD'),'max_weight':data.get('max_weight',.05 if scope=='cohort' else .65),'cost_bps':data.get('cost_bps',10.),'turnover_limit':data.get('turnover_limit',.35),'frequency':data.get('frequency','monthly'),'core_budget':data.get('core_budget',.6)}
    for k in ('max_weight','cost_bps','turnover_limit','core_budget'):
        if isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not np.isfinite(s[k]):raise ValueError('Invalid numeric setting')
        s[k]=float(s[k])
    d=date.fromisoformat(s['as_of']);r=returns_report(root,d);f=batch_report(root,d);factor=factor_report(root,d);key=hashlib.sha256(json.dumps([VERSION,r.get('return_id'),f.get('run_id'),factor.get('run_id'),s],sort_keys=True).encode()).hexdigest();base=root/'data/processed/long_only';path=base/f'{key}.json'
    try:
        out=json.loads(path.read_text())
        if out['run_id']==key and out['version']==VERSION and out['data_version']==r['return_id']:return out
    except (OSError,ValueError,KeyError):pass
    out=run_report(root,s)|{'run_id':key};base.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=base,delete=False) as f:json.dump(out,f,allow_nan=False);tmp=Path(f.name)
    tmp.replace(path);return out
