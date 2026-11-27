"""Chronological alternative research on verified common monthly returns."""
from datetime import date
from pathlib import Path
import hashlib,json,re
import numpy as np
import duckdb
from threadpoolctl import threadpool_limits
from riskmatch.strategies.alternative import (VERSION,REGISTRY,capped,rank_signal,beta,signed_rank,select_pair,pair_target,filtered_probability,ledger)
from riskmatch.strategies.long_only_report import verified_pit
from riskmatch.optimization.mean_variance_report import aligned,category
from riskmatch.profiling.mandate import validate_mandate
from riskmatch.backtesting.baselines import metrics


def macro_signals(root,version,origins):
    p=verified_pit(root,version);path=p/'macro_vintages.parquet';manifest=json.loads((p.parent/'report.json').read_text());entry=next(e for e in manifest['datasets'] if e['dataset']=='macro_vintages')
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=entry['file_hash']:raise ValueError('Macro vintage hash mismatch')
    with duckdb.connect() as db:
        rows=db.execute("SELECT instrument,observation_date,vintage_label,value FROM read_parquet(?) WHERE instrument IN ('real_output','consumer_prices')",[str(path)]).fetchall()
    vintages={}
    for s,d,label,v in rows:
        m=re.search(r'(\d{2})M(\d{1,2})$',label)
        if not m:continue
        y,mo=map(int,m.groups());y+=1900 if y>=50 else 2000
        if not 1<=mo<=12:continue
        # Vintage month is not a release timestamp: use only after its entire month elapsed.
        available=date(y+int(mo==12),mo%12+1,1)
        if d<available:vintages.setdefault(s,{}).setdefault(available,{})[d]=v
    out={}
    for day in origins:
        values=[]
        for s in ('real_output','consumer_prices'):
            possible=[v for v in vintages.get(s,{}) if v<day]
            if not possible:break
            vintage=max(possible);data=vintages[s][vintage];ds=sorted(data)
            if len(ds)<5 or (day-ds[-1]).days>370:break
            last=ds[-1];old=date(last.year-1,last.month,1)
            if old not in data or data[old]<=0:break
            values.append(data[last]/data[old]-1)
        if len(values)==2:out[day]=values
    return out


def target(key,h,u,assets,macro,pair,diagnostics=None):
    n=len(u);tick={a['ticker']:i for i,a in enumerate(assets)};etf=np.array([a['source']=='etf_crsp_monthly' for a in assets]);equity=np.array([category(a)=='equity' for a in assets]);treasury=np.array([category(a)=='treasury' for a in assets]);s=rank_signal(h);vol=np.maximum(np.std(h[-36:],axis=0,ddof=1)*np.sqrt(12),.02)
    def index(ticker):
        if ticker not in tick:
            raise ValueError(f"Missing reference return series: {ticker}")
        return tick[ticker]
    def mix(e,band=None):
        requested=e
        if band is not None:
            lo=max(band[0],1-u[treasury].sum());hi=min(band[1],u[equity].sum())
            if lo>hi+1e-9:raise ValueError('No feasible allocation within strategic tilt band')
            e=float(np.clip(e,lo,hi))
            if diagnostics is not None:diagnostics.update({'requested_equity_weight':requested,'feasible_equity_weight':e,'tilt_band':list(band)})
        a, b = equity.astype(float), treasury.astype(float)
        for sleeve, ticker, budget in ((a, "SPY", e), (b, "IEF", 1-e)):
            if ticker in tick and u[tick[ticker]] >= budget:
                sleeve[:] = 0.
                sleeve[tick[ticker]] = 1.
        return capped(a,u,e)+capped(b,u,1-e)
    def winners():
        valid=np.flatnonzero(u>0);order=valid[np.argsort(s[valid],kind='stable')];raw=np.zeros(n);raw[order[-max(1,len(order)//3):]]=1;return capped(raw,u,min(1.,u[raw>0].sum()))
    def trend():
        raw=np.where(etf&(np.prod(1+h[-12:],axis=0)>1),1/vol,0);return capped(raw,u,min(1.,u[raw>0].sum()))
    if key=='long_short':return signed_rank(s,u)
    if key=='market_neutral':return signed_rank(s,u,beta(h[-36:],h[-36:,index("SPY")]))
    if key=='global_macro':
        if macro is None:raise ValueError('No prior growth and inflation vintage')
        growth,infl=macro;rate=np.prod(1+h[-12:,index("BIL")])-1;return mix(.8 if growth>.02 and infl<.04 and rate<.05 else .3,(.3,.8))
    if key=='cta_etf_proxy':
        raw=np.where(etf,np.sign(np.prod(1+h[-12:],axis=0)-1)/vol,0);w=raw/max(np.abs(raw).sum(),1e-12);w=np.sign(w)*np.minimum(abs(w),u);v=np.std(h[-36:]@w,ddof=1)*np.sqrt(12);return w*min(1,.1/max(v,1e-9))
    if key=='statistical_arbitrage':return pair_target(h,pair,u)
    if key=='cross_sectional_momentum':return winners()
    if key=='time_series_momentum':return trend()
    if key=='mean_reversion':
        trailing=np.prod(1+h[-3:],axis=0)-1;historical=np.array([np.prod(1+h[j-3:j],axis=0)-1 for j in range(max(3,len(h)-36),len(h)-2)]);z=(trailing-historical.mean(0))/np.maximum(historical.std(0),1e-8);raw=np.where((z<=-2)&(z>-4)&(h[-1]>-.15),-z,0);return capped(raw,u,min(1.,u[raw>0].sum()))
    if key=='tactical_allocation':return mix(.6+.2*np.sign(s[index("SPY")]-s[index("IEF")]),(.4,.8))
    if key=='volatility_target':
        w=mix(.6);v=np.std(h[-36:]@w,ddof=1)*np.sqrt(12);return w*min(1.,.1/max(v,1e-9))
    if key=='all_weather':
        basket = [index(ticker) for ticker in ("SPY", "IEF", "TIP", "SHY")]
        raw = np.zeros(n)
        raw[basket] = 1 / vol[basket]
        return capped(raw, u)
    if key=='multi_strategy':
        sleeves = np.array([winners(), trend(), mix(.6)])
        sleeve_returns = h[-36:] @ sleeves.T
        cov = np.cov(sleeve_returns, rowvar=False) * 12
        volatility = np.sqrt(np.maximum(np.diag(cov), 0.))
        b = 1 / np.maximum(volatility, .02)
        b /= b.sum()
        if diagnostics is not None:
            denom = float(b @ cov @ b)
            scale = np.outer(volatility, volatility)
            corr = np.divide(cov, scale, out=np.zeros_like(cov), where=scale > 1e-24)
            diagnostics.update({
                'sleeves': ['cross_sectional_momentum', 'time_series_momentum', 'strategic_60_40'],
                'budgets': b.tolist(),
                'correlation': np.where(scale > 1e-24, np.clip(corr, -1., 1.), None).tolist(),
                'variance_contribution_shares': (b * (cov @ b) / denom).tolist() if denom > 1e-12 else None,
            })
        return b @ sleeves
    if key=='regime_switching':return mix(.2 if filtered_probability(h[:,index("SPY")])>.5 else .7,(.2,.7))
    if key=='tail_hedge_proxy':
        wealth = np.r_[1., np.cumprod(1 + h[-12:, index("SPY")])]
        drawdown = wealth[-1] / wealth.max() - 1
        return mix(.2 if drawdown < -.10 else .6)
    raise ValueError('Unsupported execution data: no validated dated futures/roll, collateral or instrument carry history')


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);scope=data.get('scope','core');currency=data.get('currency','USD');cap=data.get('max_weight',.65 if scope=='core' else .05);cost=data.get('cost_bps',10.);borrow=data.get('borrow_bps',300.);turn=data.get('turnover_limit',1.);mandate=data.get('mandate')
    if as_of>date.today() or scope not in ('core','cohort') or currency not in ('USD','CHF') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in (cap,cost,borrow,turn)) or not 0<cap<=1 or not 0<=cost<=200 or not 0<=borrow<=5000 or not 0<=turn<=2:raise ValueError('Invalid alternative settings')
    with threadpool_limits(limits=1):
        assets,intervals,x,rf,version=aligned(root,as_of,currency,scope);n=len(assets);cut=int(.8*len(x));origins=[a for a,b in intervals[cut:]];u=np.full(n,cap);unknown=[];short_ok=True;netlo=-1.5;nethi=1.;gross=1.5
        if mandate:
            m=validate_mandate(mandate);c=mandate['constraints']
            if m['conflicts'] or mandate['currency']!=currency:raise ValueError('Conflicting mandate or currency mismatch')
            hard=lambda k:c[k]['mode']=='hard' and c[k]['value'] is not None
            short_ok=c['allow_short'] and c['allow_leverage'];u=np.array([cap if category(a) in c['allowed_assets'] else 0. for a in assets]);u=np.minimum(u,c['max_asset_weight']['value']) if hard('max_asset_weight') else u
            if hard('gross_limit'):gross=min(gross,c['gross_limit']['value'])
            if hard('net_min'):netlo=c['net_min']['value']
            if hard('net_max'):nethi=min(nethi,c['net_max']['value'])
            if hard('max_turnover'):turn=min(turn,c['max_turnover']['value'])
            unknown=[k for k in ('max_issuer_weight','max_sector_weight','min_liquidity','volatility','max_cost','stress_loss','loss_budget') if hard(k)]
            if c['esg_exclusions'].strip() or c['tax_assumption']=='after_tax_required' or c['fx_hedge'] in ('partial','full'):unknown.append('ESG/tax/FX constraints not certified')
        # Strictly prior dated membership for stock targets. No lookahead from current membership.
        from riskmatch.strategies.long_only_report import load_signals
        membership,_,_=load_signals(root,as_of,assets,origins,version)
        macro=macro_signals(root,version,origins);etfs=[i for i,a in enumerate(assets) if a['ticker'] in ('SPY','IEF','SHY','TIP','BIL')];pair=select_pair(x[:cut],etfs);test=x[cut:];test_rf=rf[cut:];spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY');bw=np.zeros(n);bw[spy]=1
        def evaluate(targets,bps,bbps,limit=None):
            res=ledger(test,test_rf,targets,cost_bps=bps,borrow_bps=bbps,turnover_limit=turn if limit is None else limit)
            if res['status']!='computed':return res
            r=res.pop('returns');l=res['ledger'];
            for row,(a,b) in zip(l,intervals[cut:]):row.update({'start':str(a),'end':str(b)})
            return res|{'net':metrics(r,test_rf),'nav':np.cumprod(1+r).tolist(),'realized_beta':float(beta(r[:,None],test[:,spy])[0]),'average_gross':float(np.mean([v['gross'] for v in l])),'average_net':float(np.mean([v['net'] for v in l])),'transaction_fees':sum(v['fee'] for v in l),'borrow_fees':sum(v['borrow'] for v in l),'funding_fees':sum(v['funding'] for v in l)}
        rows={}
        for key in REGISTRY:
            try:
                targets=[];diagnostics={}
                for j,d in enumerate(origins):
                    cu=u.copy()
                    for i,a in enumerate(assets):
                        if a['source']=='stock_monthly' and str(a['instrument']) not in membership.get(d,set()):cu[i]=0.
                    w=target(key,x[:cut+j],cu,assets,macro.get(d),pair,diagnostics)
                    if np.any(abs(w)>cu+1e-8) or np.abs(w).sum()>gross+1e-8 or not netlo-1e-8<=w.sum()<=nethi+1e-8:raise ValueError('Mandate exposure/cap violation')
                    if (w< -1e-9).any() and not short_ok:raise ValueError('Short/leverage disallowed')
                    if mandate and unknown:raise ValueError('Uncertified hard mandate constraints: '+', '.join(unknown))
                    targets.append(w)
                res=evaluate(targets,cost,borrow)
                if res['status']=='computed':
                    grossres=evaluate(targets,0.,0.);shock=evaluate(targets,max(25,cost),min(5000,max(600,borrow*2)));res['gross_cagr']=grossres.get('net',{}).get('cagr');res['cost_shock_cagr']=shock.get('net',{}).get('cagr');res['last_holdings']=[{'ticker':a['ticker'],'weight':float(w)} for a,w in zip(assets,targets[-1]) if abs(w)>1e-8];res['diagnostics']=diagnostics
                    shock_vectors={'equity_crash':np.array([-.30 if category(a)=='equity' else .02 if category(a)=='treasury' else -.10 for a in assets]),'inflation_rate_shock':np.array([-.15 if category(a)=='equity' else -.12 if a['ticker']=='IEF' else -.05 if category(a)=='treasury' else -.10 for a in assets]),'short_squeeze':np.where(np.asarray(targets[-1])<0,.50,0.)};res['scenario_returns']={k:float(v@targets[-1]) for k,v in shock_vectors.items()};res['annual_turnover']=float(sum(q['turnover'] for q in res['ledger'][1:])*12/len(test))
                    # One additional month delay, cash at initial test date; diagnostic only, not mandate executable.
                    delayed=evaluate([np.zeros(n),*targets[:-1]],cost,borrow,2.);res['lagged_cagr']=delayed.get('net',{}).get('cagr')
                rows[key]=res
            except (ValueError,ArithmeticError) as e:rows[key]={'status':'unavailable','reason':str(e)}
        benchmark=ledger(test,test_rf,[bw]*len(test),cost_bps=cost,borrow_bps=0);br=benchmark['returns'];bench={'net':metrics(br,test_rf),'nav':np.cumprod(1+br).tolist()};sw=np.zeros(n);sw[spy]=.6;sw[next(i for i,a in enumerate(assets) if a['ticker']=='IEF')]=.4;strategic=ledger(test,test_rf,[sw]*len(test),cost_bps=cost,borrow_bps=0)['returns'];return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'asset_count':n,'currency':currency,'scope':scope,'train_months':cut,'test_months':len(test),'first':str(origins[0]),'last':str(intervals[-1][1]),'macro_dates':len(macro),'pair':None if pair is None else [assets[pair[1]]['ticker'],assets[pair[2]]['ticker']],'registry':REGISTRY,'strategies':rows,'benchmark':bench,'cash_benchmark':metrics(test_rf,test_rf),'strategic_benchmark':metrics(strategic,test_rf),'configuration':{'max_weight':cap,'cost_bps':cost,'borrow_bps':borrow,'turnover_limit':turn},'warning':'Static retrospective endpoint cohort; monthly signals use prior closes, hypothetical fills. Borrow availability, margin, liquidity and intramonth stop checks unverified. CHF BIL proxy not risk-free. Macro vintage month lagged, exact release time unverified. External reference portfolios exempt from candidate caps. No real orders.'}
