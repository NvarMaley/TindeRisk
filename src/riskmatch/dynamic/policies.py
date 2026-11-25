"""Research-only dynamic allocation between a matched portfolio and USD cash."""
import numpy as np

VERSION = "dynamic-v1"
POLICIES = ("hmm", "bayesian", "risk_budget", "stochastic", "multi_period",
            "dynamic_programming", "mpc", "reinforcement_learning", "ensemble", "robust_control")
GRID = np.linspace(0, 1, 11)


def beliefs(history):
    """Fixed two-state Gaussian filter and conjugate Bernoulli posterior."""
    p = .5
    for observation in history:
        prior = .08 + .84*p
        log_likelihood = -.5*((observation-np.array([.008,-.02]))/np.array([.025,.065]))**2-np.log([.025,.065])
        likelihood = np.exp(log_likelihood-log_likelihood.max())
        posterior = np.array([1-prior,prior])*likelihood
        p = posterior[1]/posterior.sum()
    return float(p), float((1+sum(history<0))/(2+len(history)))


def targets(history, current, cost, volatility_limit=.10, uncertainty=1.):
    """All estimators use past monthly excess returns only; decisions are grid fractions."""
    h = np.asarray(history,float)
    if h.ndim!=1 or len(h)<12 or not np.isfinite(h).all():
        raise ValueError("At least 12 finite prior observations required")
    g = GRID
    mu, var = h.mean(), max(h.var(ddof=1),1e-10)
    bad, bayes = beliefs(h)
    reward = g*mu-3*g*g*var
    trade = cost*abs(g-current)
    transition = cost*abs(g[:,None]-g[None,:])
    scenarios = h[:,None]*g
    utility = np.mean(scenarios-3*scenarios**2,axis=0)
    # Three-step Markov Bellman recursion over regime and prior allocation.
    conditional=np.array([h[h>=0].mean() if np.any(h>=0) else mu,
                          h[h<0].mean() if np.any(h<0) else mu])
    regime_reward=conditional[:,None]*g-3*var*g*g
    markov=np.array([[.92,.08],[.08,.92]])
    value = np.zeros((2,len(g)))
    for _ in range(3):
        value = np.max(regime_reward[:,None,:]-transition[None,:,:]+(markov@value)[:,None,:],axis=2)
    expected_next=np.array([1-bad,bad])@markov@value
    # Open-loop multi-period policy: jointly choose three allocations.
    sequences=np.stack(np.meshgrid(g,g,g,indexing="ij"),axis=-1).reshape(-1,3)
    switching=abs(sequences[:,0]-current)+abs(np.diff(sequences,axis=1)).sum(axis=1)
    def plan(forecasts):
        payoff=(sequences*np.asarray(forecasts)-3*var*sequences**2).sum(axis=1)-cost*switching
        return float(sequences[np.argmax(payoff),0])
    # Tabular Q-learning on chronological, already observed returns.
    q = np.zeros((2,len(g)))
    for t in range(1,len(h)):
        state,next_state = int(h[t-1]<0),int(h[t]<0)
        net = g*h[t]-3*(g*h[t])**2-cost*g
        q[state] += .15*(net+.8*q[next_state].max()-q[state])
    pick=lambda u: float(g[np.argmax(u)])
    result = {
        "hmm": 1-bad,
        "bayesian": 1-bayes,
        "risk_budget": min(1.,volatility_limit/np.sqrt(12*var)),
        "stochastic": pick(utility-trade),
        "multi_period": plan([mu,mu,mu]),
        "dynamic_programming": pick(reward-trade+expected_next),
        "mpc": plan([h[-6:].mean(),.5*h[-6:].mean()+.5*mu,mu]),
        "reinforcement_learning": pick(q[int(h[-1]<0)]-trade),
        "robust_control": pick(reward-uncertainty*g*np.sqrt(var/len(h))-trade),
    }
    result["ensemble"]=float(np.mean(list(result.values())))
    return result


def simulate(returns,cash,dates,start,capital,policy,weights,stress_limit,stress_loss,
             cost_bps=10.,contribution=0.,withdrawal=0.,frequency=1,drift=.05):
    """One-month lag, self-financing ledger, beginning-of-month external flows."""
    x=np.asarray(returns,float);rf=np.asarray(cash,float)
    if x.ndim!=2 or rf.shape!=(len(x),) or len(dates)!=len(x) or not np.isfinite(x).all() or not np.isfinite(rf).all() or np.any(x<=-1) or np.any(rf<=-1):
        raise ValueError("Invalid aligned returns")
    a=np.asarray(weights,float)
    if a.shape!=(x.shape[1],) or np.any(a<0) or not np.isclose(a.sum(),1) or start<13 or start>=len(x) or not np.isfinite([capital,cost_bps,contribution,withdrawal,stress_limit,stress_loss,drift]).all() or capital<=0 or not 0<=cost_bps<=100 or frequency not in (1,3) or not 0<=drift<=1 or min(contribution,withdrawal,stress_limit,stress_loss)<0:
        raise ValueError("Invalid dynamic configuration")
    if policy not in ("static","drift",*POLICIES):
        raise ValueError("Unknown policy")
    base=x@a; max_fraction=min(1.,stress_limit/stress_loss) if stress_loss>0 else 1.
    holdings=np.r_[np.zeros(len(a)),capital]; rows=[]; performance=[]; fees=0.;turnover=0.
    for t in range(start,len(x)):
        opening=float(holdings.sum()); flow=contribution-withdrawal
        if opening+flow<=0:
            return {"status":"shortfall","ledger":rows,"shortfall":float(max(0.,-(opening+flow))),"fees":fees}
        holdings[-1]+=flow
        previous=holdings/holdings.sum(); current=float(previous[:-1].sum())
        history=(base-rf)[max(0,t-61):t-1]
        desired=max_fraction if policy in ("static","drift") else min(max_fraction,targets(history,current,cost_bps/10000)[policy])
        target=np.r_[desired*a,1-desired]
        trade=t==start or holdings[-1]<0 or current>max_fraction+1e-8 or (policy=="drift" and np.max(abs(target-previous))>drift) or (policy!="drift" and (t-start)%frequency==0)
        fee=0.;notional=0.;delta=np.zeros(len(a))
        if trade:
            from riskmatch.backtesting.walk_forward import execute
            holdings,delta,fee=execute(holdings,target,cost_bps/10000)
            notional=float(abs(delta).sum());turnover+=notional/(opening+flow);fees+=fee
        invested=float(holdings.sum());executed=holdings/invested
        holdings*=1+np.r_[x[t],rf[t]]
        end=float(holdings.sum());r=end/(opening+flow)-1
        if not np.isclose(end,opening+flow-fee+float((executed*invested)@np.r_[x[t],rf[t]])):
            raise ArithmeticError("Ledger reconciliation failed")
        performance.append(r)
        trailing=np.column_stack([x[max(0,t-61):t-1],rf[max(0,t-61):t-1]])@executed
        rows.append(dict(date=str(dates[t]),opening=opening,flow=flow,fee=fee,ending=end,
                         pnl=end-invested,trade_deltas=delta.tolist(),end_positions=holdings.tolist(),
                         fraction=float(executed[:-1].sum()),target_fraction=desired,
                         drift=float(np.max(abs(target-previous))),trade=bool(trade),
                         stress_estimate=float(executed[:-1].sum()*stress_loss),
                         annual_volatility=float(np.std(trailing,ddof=1)*np.sqrt(12)),
                         expected_shortfall_estimate=float(-np.sort(trailing)[:max(1,int(np.ceil(.05*len(trailing))))].mean()),
                         concentration=float(max(executed)),cash_reserve=float(executed[-1]),
                         weights=executed.tolist(),proposed_weights=target.tolist(),model=policy,
                         turnover=notional/(opening+flow),return_=r))
    r=np.asarray(performance);nav=np.r_[1.,np.cumprod(1+r)]
    return dict(status="computed",ledger=rows,fees=fees,ending=float(holdings.sum()),
                cagr=float(nav[-1]**(12/len(r))-1),volatility=float(r.std(ddof=1)*np.sqrt(12)) if len(r)>1 else 0.,
                drawdown=float((nav/np.maximum.accumulate(nav)-1).min()),
                expected_shortfall=float(np.sort(r)[:max(1,int(np.ceil(.05*len(r))))].mean()*-1),
                annual_turnover=turnover*12/len(r),nav=nav.tolist())
