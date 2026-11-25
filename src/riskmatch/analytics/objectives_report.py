"""Fixed historical references, not an optimized or tradable recommendation."""
from datetime import date
import numpy as np
import duckdb
from riskmatch.analytics.descriptive_report import selected_source
from riskmatch.analytics.objectives import VERSION, SPECS, bootstrap_indices, evaluate
from riskmatch.analytics.tail_risk import empirical, drawdown
from riskmatch.profiling.mandate import validate_mandate, add_month, years_between

TICKERS=('SPY','SHY','BIL','TIP')
IDS=('84398','89470','92027','89959')
REFERENCES={'capital_reference':(0,.60,.40,0),'balanced_reference':(.5,.3,.1,.1),'growth_reference':(.8,.1,.05,.05),'inflation_reference':(.2,.2,.1,.5)}


def objective_report(root,mandate):
    report=validate_mandate(mandate)
    if report['conflicts']:raise ValueError('Mandate has structural conflicts')
    as_of=date.fromisoformat(report['as_of']);end=date.fromisoformat(report['horizon_date'])
    if as_of>date.today():raise ValueError('Future mandate date')
    months=1
    while add_month(as_of,months)<end:months+=1
    # Bounded local simulation. Longer horizons remain explicitly unavailable.
    if months>600:raise ValueError('Scenario horizon exceeds 50 years')
    path,entry=selected_source(root,'etf_crsp_monthly',as_of)
    suffix='_chf' if report['currency']=='CHF' else '';total='total_return'+suffix;price='price_return'+suffix
    maps=[]
    with duckdb.connect() as db:
        for instrument in IDS:
            rows=db.execute(f'SELECT start_date,end_date,{total},{price} FROM read_parquet(?) WHERE instrument=? AND end_date<=? AND (availability_time IS NULL OR CAST(availability_time AS DATE)<=?) ORDER BY end_date',[str(path),instrument,as_of,as_of]).fetchall()
            maps.append({(a,b):(v,p) for a,b,v,p in rows if a is not None and b is not None and v is not None and p is not None and np.isfinite([v,p]).all() and v> -1})
    common=sorted(set.intersection(*(set(m) for m in maps)))
    if len(common)<120:raise ValueError('At least 120 aligned monthly total and price returns required')
    x=np.array([[m[i][0] for m in maps] for i in common]);p=np.array([[m[i][1] for m in maps] for i in common]);cut=int(.8*len(x));starts=[i for i in range(cut-5) if all(common[j][1]==common[j+1][0] for j in range(i,i+5))];indices=bootstrap_indices(cut,months,paths=2000,valid_starts=starts)
    test_continuous=all(common[j][1]==common[j+1][0] for j in range(cut,len(common)-1));gap_count=sum(common[j][1]!=common[j+1][0] for j in range(len(common)-1))
    refs=[];constraints=mandate['constraints']; shock=None if mandate['inflation'] is None else min(1,mandate['inflation']+.02)
    # Transparent flat-rate reference only, not a fitted liability discount curve.
    flat_rate=float(np.exp(12*np.log1p(x[:cut,2]).mean())-1)
    liabilities=[(date.fromisoformat(v['date']),v['amount']) for v in mandate['dated_flows'] if v['kind']=='liability']
    liabilities.extend((date.fromisoformat(g['due_date']),g['target_nominal_base']) for g in report['goals'] if g['objective_id']=='OBJ09' and g['funding'])
    def pv(rate):return sum(a/(1+rate)**years_between(as_of,d) for d,a in liabilities)
    liability_reference={'flat_discount_rate':flat_rate,'pv':pv(flat_rate),'capital_minus_liability_pv':mandate['capital']-pv(flat_rate),'liability_dv01':(pv(flat_rate-.0001)-pv(flat_rate+.0001))/2,'asset_dv01':None,'mismatch':None} if liabilities else None
    for name,weights in REFERENCES.items():
        w=np.array(weights);r=x@w;sample=r[indices];cash=x[:,2][indices];proxy=((x-p)@w)[indices]
        evaluation=evaluate(mandate,sample,cash,distribution_proxy=proxy,report=report)
        risk={'train_annual_volatility':float(np.std(r[:cut],ddof=1)*np.sqrt(12)),'train_annual_mean':float(r[:cut].mean()*12),'train_monthly_es95':empirical(-r[:cut],.95)['es'],'test_annual_volatility':float(np.std(r[cut:],ddof=1)*np.sqrt(12)),'test_realized_cumulative':float(np.prod(1+r[cut:])-1) if test_continuous else None,'test_max_drawdown':drawdown(r[cut:],[i[1] for i in common[cut:]])['maximum'] if test_continuous else None}
        failures=[];unknown=[]
        allowed=set(constraints['allowed_assets']);needed={'equity'} if w[0]>0 else set();needed|={'treasury'} if any(w[1:]>0) else set()
        if not needed<=allowed:failures.append('allowed_assets')
        checks={'max_asset_weight':float(w.max()),'gross_limit':1.,'net_min':1.,'net_max':1.,'volatility':risk['train_annual_volatility']}
        for k,lim in constraints.items():
            if not isinstance(lim,dict) or lim['value'] is None or lim['mode']!='hard':continue
            if k in checks:
                if (checks[k]<lim['value'] if k=='net_min' else checks[k]>lim['value']+1e-10):failures.append(k)
            else:unknown.append(k)
        if constraints['esg_exclusions'].strip():unknown.append('esg_exclusions')
        if constraints['tax_assumption']=='after_tax_required':unknown.append('tax_assumption')
        if constraints['fx_hedge'] in ('partial','full'):unknown.append('fx_hedge')
        sensitivity=None
        if shock is not None:
            shocked=mandate|{'inflation':shock};s=evaluate(shocked,sample,cash,distribution_proxy=proxy)
            sensitivity={'inflation':shock,'goals':[{'index':g['index'],'probability':g['probability'],'expected_deficit':g['expected_deficit'],'real_mean_wealth':g['metrics']['real_mean_wealth']} for g in s['goals']]}
        refs.append({'id':name,'weights':dict(zip(TICKERS,weights)),'risk':risk,'eligibility':'fails_known_constraint' if failures else 'unverified','failed_constraints':failures,'unverified_constraints':unknown,'evaluation':evaluation,'inflation_shock':sensitivity})
    return {'version':VERSION,'status':'experimental','approved':False,'currency':report['currency'],'source':'etf_crsp_monthly','point_in_time_verified':False,'first':str(common[0][0]),'last':str(common[-1][1]),'training_end':str(common[cut-1][1]),'training_count':cut,'test_count':len(common)-cut,'historical_gap_count':gap_count,'continuous_training_blocks':len(starts),'block_months':6,'paths':2000,'seed':12,'objectives':{k:{'function':v[0],'constraint_or_limitation':v[1]} for k,v in SPECS.items()},'required_returns':report['goals'],'combined_required_return':report['combined_required_return'],'liability_reference':liability_reference,'references':refs,'warning':'Retrospective archive: original publication timestamps missing. Conditional block-bootstrap illustrations; no forecast guarantee, cash dividend proxy is not net income, gross of trading/taxes, no portfolio suitability or hedge certification.'}
