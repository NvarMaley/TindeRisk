"""Dated goal evaluation on unchanged, illustrative candidate scenarios."""
from dataclasses import dataclass
from datetime import date
import numpy as np
from riskmatch.profiling.mandate import add_month, years_between, validate_mandate, OBJECTIVES
from riskmatch.analytics.tail_risk import empirical

VERSION='objectives-v1'
SPECS={
 'OBJ01':('minimize capital loss probability and deficit','nominal and real capital floor'),
 'OBJ02':('maximize cash income coverage and stability','dated withdrawals; distribution cash data required'),
 'OBJ03':('minimize volatility and expected shortfall','hard loss and liquidity limits'),
 'OBJ04':('maximize mean minus risk penalty','mean-variance utility; risk budget separate'),
 'OBJ05':('maximize expected terminal wealth and real CAGR','funding and eligibility constraints'),
 'OBJ06':('maximize growth within budget','volatility, ES and leverage limits separate'),
 'OBJ07':('maximize real return and purchasing power','inflation scenario, CPI beta requires time series'),
 'OBJ08':('maximize excess return over cash','cash proxy and downside risk'),
 'OBJ09':('minimize dated liability shortfall','PV and DV01 require curve and instrument cash flows'),
 'OBJ10':('maximize goal probability; minimize deficit','dated funding goals'),
 'OBJ11':('minimize loss below explicit floor','no guarantee; hedge cost and gap risk require hedge contract'),
}

@dataclass(frozen=True)
class Goal:
    index:int
    objective_id:str
    due:date
    target:float|None
    funding:bool
    priority:int
    penalty:float


def goal_specs(report):
    return [Goal(g['goal_index'],g['objective_id'],date.fromisoformat(g['due_date']),g['target_nominal_base'],g['funding'],g['priority'],g['shortfall_penalty']) for g in report['goals']]


def bootstrap_indices(n,months,paths=2000,block=6,seed=12,valid_starts=None):
    if n<block or months<1 or not 1<=paths<=10000:raise ValueError('Insufficient scenario history')
    rng=np.random.default_rng(seed)
    allowed=np.arange(n-block+1) if valid_starts is None else np.asarray(valid_starts,int)
    if len(allowed)==0 or np.any(allowed<0) or np.any(allowed>n-block):raise ValueError('No continuous scenario blocks')
    starts=rng.choice(allowed,size=(paths,(months+block-1)//block))
    return (starts[:,:,None]+np.arange(block)).reshape(paths,-1)[:,:months]


def evaluate(mandate,monthly_returns,cash_returns,*,distribution_proxy=None,report=None,include_wealth_path=False,discount_rate=None):
    """Inputs: same paths × months of decimal returns, base currency. No borrowing.

    Monthly return accrues geometrically between dated events. Funding is paid in
    descending priority then input order, subject to available wealth. Any missed
    withdrawal is recorded, never silently borrowed or credited later.
    """
    report=report or validate_mandate(mandate)
    if report['conflicts']:raise ValueError('Mandate has structural conflicts')
    r=np.asarray(monthly_returns,float); cash=np.asarray(cash_returns,float)
    if r.ndim!=2 or cash.shape!=r.shape or not np.isfinite(r).all() or not np.isfinite(cash).all() or np.any(r<=-1) or np.any(cash<=-1):raise ValueError('Invalid scenario paths')
    start=date.fromisoformat(report['as_of']);end=date.fromisoformat(report['horizon_date']);initial=float(mandate['capital']); inflation=mandate['inflation']
    bounds=[start];m=1
    while bounds[-1]<end:bounds.append(min(add_month(start,m),end));m+=1
    months=len(bounds)-1
    if r.shape[1]!=months:raise ValueError('Scenario horizon mismatch')
    n=len(r);goals=goal_specs(report); wealth=np.full(n,initial); unmet=np.zeros(n); unmet_withdrawal=np.zeros(n); unmet_liability=np.zeros(n); income_paid=np.zeros(n); income_due=0.; snapshots={}; flow_events={}
    for row in mandate['dated_flows']:
        date_=date.fromisoformat(row['date']);flow_events.setdefault(date_,[]).append((row['kind'],float(row['amount'])))
    for i in range(1,months+1):
        when=add_month(start,i)
        if when<=end:flow_events.setdefault(when,[]).extend([('contribution',mandate['contribution_monthly']),('withdrawal',mandate['withdrawal_monthly'])])
    goal_events={}
    for g in goals:goal_events.setdefault(g.due,[]).append(g)
    market=np.ones(n);cash_market=np.ones(n);peak=np.ones(n);max_loss=np.zeros(n);market_snap={}; monthly_income=[]; income_schedule=[]; liability_schedule=[]; withdrawal_schedule=[]
    dist=None if distribution_proxy is None else np.asarray(distribution_proxy,float)
    if dist is not None and (dist.shape!=r.shape or not np.isfinite(dist).all()):raise ValueError('Invalid distribution proxy')
    wealth_path = [[initial] * 3] if include_wealth_path else None
    nominal_net_flows = np.zeros(n)
    discounted_net_flows = np.zeros(n)
    funded_goal_schedule = []
    for k,(left,right) in enumerate(zip(bounds,bounds[1:])):
        # Last partial month uses the fraction of the actual full anniversary interval.
        full_right=add_month(start,k+1);days=(full_right-left).days; prev=left
        opening=wealth.copy()
        if dist is not None:monthly_income.append(opening*dist[:,k]*(right-left).days/days)
        scheduled=sorted({d for d in flow_events.keys()|goal_events.keys() if left<d<=right}|{right})
        for when in scheduled:
            fraction=(when-prev).days/days; growth=np.power(1+r[:,k],fraction)
            wealth*=growth;market*=growth;cash_market*=np.power(1+cash[:,k],fraction);peak=np.maximum(peak,market);max_loss=np.maximum(max_loss,1-market/peak);prev=when
            events=flow_events.get(when,[])
            contributions=sum(a for typ,a in events if typ=='contribution')
            wealth+=contributions
            net_flow = np.full(n, -contributions, dtype=float) if wealth_path is not None else None
            for typ in ('liability','withdrawal'):
                due=sum(a for t,a in events if t==typ)
                paid=np.minimum(wealth,due);wealth-=paid;unmet+=due-paid
                if net_flow is not None:
                    net_flow += paid
                if due:
                    if typ=='withdrawal':
                        income_paid+=paid;income_due+=due;unmet_withdrawal+=due-paid;withdrawal_schedule.append({'date':str(when),'due':due,'mean_paid':float(paid.mean())})
                    else:unmet_liability+=due-paid;liability_schedule.append({'date':str(when),'due':due,'mean_paid':float(paid.mean())})
            # Non-funding targets are evaluated before spending funding goals at this date.
            for g in sorted(goal_events.get(when,[]),key=lambda g:(g.funding,-g.priority,g.index)):
                target=g.target
                if g.objective_id=='OBJ01' and target is None:target=initial
                if target is not None and g.objective_id!='OBJ02':
                    avail=wealth.copy();deficit=np.maximum(target-avail,0);success=avail>=target-1e-8
                    snapshots[g.index]=(avail,deficit,success,target)
                    if g.funding:
                        paid_goal = np.minimum(wealth,target)
                        wealth -= paid_goal
                        unmet += deficit
                        if net_flow is not None:
                            net_flow += paid_goal
                            funded_goal_schedule.append({"objective_id":g.objective_id, "date":str(when),
                                                          "median_paid":float(np.median(paid_goal))})
                else:snapshots[g.index]=(wealth.copy(),None,None,None)
                market_snap[g.index]=(market.copy(),cash_market.copy(),max_loss.copy(),income_paid.copy(),income_due,unmet_liability.copy(),unmet_withdrawal.copy())
            if net_flow is not None:
                nominal_net_flows += net_flow
                if discount_rate is not None:
                    discounted_net_flows += net_flow / (1 + discount_rate)**years_between(start, when)
        if dist is not None:income_schedule.append({'date':str(right),'mean_distribution_proxy':float(monthly_income[-1].mean())})
        if wealth_path is not None:
            wealth_path.append(np.quantile(wealth, [.05, .5, .95]).tolist())
    out=[]
    for g in goals:
        avail,deficit,success,target=snapshots[g.index];mkt,benchmark,dd,paid,due,liabgap,withdrawgap=market_snap[g.index];years=years_between(start,g.due)
        real_factor=(1+inflation)**years if inflation is not None else None
        market_cagr=mkt**(1/years)-1
        metrics={'mean_wealth':float(avail.mean()),'real_mean_wealth':float(avail.mean()/real_factor) if real_factor else None,'market_cagr':float(market_cagr.mean()),'real_market_cagr':float(np.mean((mkt/real_factor)**(1/years)-1)) if real_factor else None,'mean_drawdown':float(dd.mean()),'loss_budget_breach_probability':float(np.mean(dd>report['effective_stress_limit'])),'nominal_capital_loss_probability':float(np.mean(mkt<1)),'nominal_capital_deficit':float(initial*np.maximum(1-mkt,0).mean()),'real_capital_loss_probability':float(np.mean(mkt<real_factor)) if real_factor else None,'real_capital_deficit':float(initial*np.maximum(1-mkt/real_factor,0).mean()) if real_factor else None,'withdrawal_coverage':float(paid.mean()/due) if due else None,'expected_unpaid_liability':float(liabgap.mean()),'expected_unpaid_withdrawals':float(withdrawgap.mean())}
        past=[i for i,b in enumerate(bounds[1:]) if b<=g.due]
        k=len(past)
        metrics['cash_excess_cagr']=float(np.mean(market_cagr-(benchmark**(1/years)-1)))
        metrics['downside_utility']=float(np.mean(np.maximum(1-mkt,0)**2));metrics['terminal_loss_es95']=empirical(1-mkt,.95)['es'] if n>=100 else None
        metrics['annual_cagr_dispersion']=float(np.std(market_cagr));metrics['mean_variance_utility_reference']={str(lam):float(market_cagr.mean()-.5*lam*np.var(market_cagr)) for lam in (1,3,10)}
        metrics['distribution_proxy_mean']=float(sum(v.mean() for v in monthly_income[:k])) if dist is not None else None
        if dist is not None and k:
            cumulative=np.sum(monthly_income[:k],axis=0)
            metrics['distribution_proxy_volatility']=float(np.std(cumulative))
            metrics['income_target_proxy_coverage']=float(cumulative.mean()/g.target) if g.objective_id=='OBJ02' and g.target else None
        probability=float(success.mean()) if success is not None else None
        gap=float(deficit.mean()) if deficit is not None else None
        # Dimensionless penalty: deficit / target; preference weight remains separate.
        loss=gap/target if target and gap is not None else None
        out.append({'index':g.index,'objective_id':g.objective_id,'due_date':str(g.due),'funding':g.funding,'target':target,'probability':probability,'probability_mc_se':float(np.sqrt(probability*(1-probability)/n)) if probability is not None else None,'expected_deficit':gap,'funding_ratio':float(avail.mean()/target) if target else None,'wealth_quantiles':np.quantile(avail,[.05,.5,.95]).tolist(),'normalized_shortfall':loss,'priority':g.priority,'penalty':g.penalty,'metrics':metrics,'limitations':SPECS[g.objective_id][1]})
    total=sum(g.priority for g in goals);weighted=0.;covered=0.
    for g in out:
        g['weight']=g['priority']/total
        if g['normalized_shortfall'] is not None:weighted+=g['weight']*g['penalty']*g['normalized_shortfall'];covered+=g['weight']
    result = {'goals':out,'weighted_target_penalty':weighted if covered else None,'target_weight_coverage':covered,'mean_terminal_wealth':float(wealth.mean()),'terminal_quantiles':np.quantile(wealth,[.05,.5,.95]).tolist(),'mean_unpaid_obligations':float(unmet.mean()),'all_obligations_paid_probability':float(np.mean(unmet<=1e-8)),'withdrawal_schedule':withdrawal_schedule,'liability_schedule':liability_schedule,'income_proxy_schedule':income_schedule,'paths':n,'months':months}
    if wealth_path is not None:
        years = years_between(start, end)
        cagr = market ** (1 / years) - 1
        gains = wealth + nominal_net_flows - initial
        result.update(wealth_path={"dates": [str(day) for day in bounds], "bands": wealth_path},
                      market_cagr_quantiles=np.quantile(cagr, [.05, .5, .95]).tolist(),
                      mean_market_cagr=float(cagr.mean()),
                      net_gain_quantiles=np.quantile(gains, [.05, .5, .95]).tolist(),
                      mean_net_gain=float(gains.mean()),
                      funded_goal_schedule=funded_goal_schedule,
                      market_loss_probability=float(np.mean(market < 1.)),
                      drawdown_threshold=report["effective_stress_limit"],
                      drawdown_breach_probability=float(np.mean(max_loss > report["effective_stress_limit"])))
        if inflation is not None:
            real_factor = (1 + inflation)**years
            result["purchasing_power"] = {
                "inflation": inflation,
                "terminal_quantiles": np.quantile(wealth / real_factor, [.05, .5, .95]).tolist(),
                "market_cagr_quantiles": np.quantile((market / real_factor)**(1 / years) - 1, [.05, .5, .95]).tolist(),
            }
        if discount_rate is not None:
            present_wealth = wealth / (1 + discount_rate)**years
            present_gains = present_wealth + discounted_net_flows - initial
            result["present_value"] = {
                "rate": discount_rate,
                "terminal_quantiles": np.quantile(present_wealth, [.05, .5, .95]).tolist(),
                "net_gain_quantiles": np.quantile(present_gains, [.05, .5, .95]).tolist(),
                "mean_net_gain": float(present_gains.mean()),
            }
    return result
