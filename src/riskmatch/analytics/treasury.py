"""Conditional Treasury valuation; USD per 100 original face, decimal yields."""
from calendar import monthrange
from datetime import date
import numpy as np
from scipy.optimize import brentq, linprog

VERSION='treasury-v1'
KEYS=np.array([.5,2.,5.,10.,30.])


def shift_month(d,n):
    y,m=divmod(d.year*12+d.month-1+n,12);m+=1
    return date(y,m,monthrange(y,m)[1] if d.day==monthrange(d.year,d.month)[1] else min(d.day,monthrange(y,m)[1]))


def schedule(issue,maturity,settlement,coupon,kind,dated_date=None):
    if not issue<=settlement<maturity or not np.isfinite(coupon) or coupon<0:raise ValueError('Invalid security dates or coupon')
    if kind=='treasury_bill':
        if coupon!=0:raise ValueError('Bill must have zero coupon')
        return [(maturity,100.,(maturity-settlement).days/365)],0.
    if kind not in ('treasury_note','treasury_bond','tips'):raise ValueError('Unsupported security type')
    dates=[];i=0
    while True:
        d=shift_month(maturity,-6*i)
        if d<=settlement:break
        dates.append(d);i+=1
    nxt=dates[-1];prior=d
    if prior<(dated_date or issue):raise ValueError('Initial irregular coupon period not verified')
    frac=(nxt-settlement).days/(nxt-prior).days;accrued=50*coupon*(1-frac)
    flows=[(d,50*coupon+(100 if d==maturity else 0),(.5*(frac+j))) for j,d in enumerate(reversed(dates))]
    return flows,accrued


def yield_price(flows,y):
    if y<=-2:raise ValueError('Invalid semiannual yield')
    return float(sum(cf*(1+y/2)**(-2*t) for _,cf,t in flows))


def yield_metrics(flows,clean,accrued,ratio=1.):
    dirty=clean+accrued
    if dirty<=0 or ratio<=0 or not np.isfinite([dirty,ratio]).all():raise ValueError('Invalid price/index ratio')
    y=brentq(lambda z:yield_price(flows,z)-dirty,-.5,10.)
    t=np.array([v[2] for v in flows]);cf=np.array([v[1] for v in flows]);pv=cf*(1+y/2)**(-2*t)
    mac=float(t@pv/dirty);mod=mac/(1+y/2);conv=float(np.sum(t*(t+.5)*pv)/(dirty*(1+y/2)**2));b=.0001
    down,up=yield_price(flows,y-b),yield_price(flows,y+b)
    return {'clean_per_100':clean,'accrued_per_100':accrued,'dirty_per_100':dirty,'indexed_dirty_per_100':dirty*ratio,'indexed_accrued_per_100':accrued*ratio,'yield':float(y),'macaulay_duration':mac,'modified_duration':mod,'yield_effective_duration':(down-up)/(2*dirty*b),'convexity':conv,'dv01_per_100':(down-up)/2*ratio,'yield_shocks':{str(bp):yield_price(flows,y+bp/10000)/dirty-1 for bp in (-200,-100,-50,50,100,200)}}


def bootstrap(par):
    """Semiannual par bootstrap after interpolating sparse observed par nodes.

    Sub-6m rates are money-market proxies, not observed zero prices. Real
    short par rates extrapolate first observed maturity flat.
    """
    nodes=np.array(sorted(par));rates=np.array([par[x] for x in nodes]);grid=np.arange(.5,30.01,.5);df=[]
    if nodes[-1]<30 or not np.isfinite(rates).all():raise ValueError('Incomplete par curve')
    for t in grid:
        c=float(np.interp(t,nodes,rates))/2;v=(1-c*sum(df))/(1+c)
        if not np.isfinite(v) or v<=0:raise ValueError('Nonpositive bootstrapped discount factor')
        df.append(v)
    short=nodes[nodes<.5];return np.r_[0.,short,grid],np.r_[1.,[1/(1+par[t]*t) for t in short],df]


def discount(curve,t):
    x,d=curve;t=np.asarray(t,float)
    if (t<0).any() or (t>x[-1]+.01).any():raise ValueError('Cashflow outside curve')
    return np.exp(np.interp(t,x,np.log(d)))


def curve_metrics(flows,settlement,dirty,curve,ratio=1.):
    t=np.array([(d-settlement).days/365.25 for d,_,_ in flows]);cf=np.array([v for _,v,_ in flows]);base=discount(curve,t)
    z=brentq(lambda s:float(cf@(base*np.exp(-s*t)))-dirty,-.5,10.);pv=cf*base*np.exp(-z*t)
    def shock(b):return float(pv@np.exp(-np.asarray(b)*t))
    b=.0001;up,down=shock(b),shock(-b);kr={}
    for i,k in enumerate(KEYS):
        shape=np.interp(t,KEYS,np.eye(len(KEYS))[i]);kr[str(k)]=(shock(-b*shape)-shock(b*shape))/(2*dirty*b)
    return {'z_spread':float(z),'effective_duration':(down-up)/(2*dirty*b),'effective_convexity':(down+up-2*dirty)/(dirty*b*b),'curve_dv01_per_100':(down-up)*ratio/2,'key_rate_duration':kr,'key_rate_dv01':{k:v*dirty*ratio*b for k,v in kr.items()},'curve_shocks':{'parallel_up_100bp':shock(.01)/dirty-1,'parallel_down_100bp':shock(-.01)/dirty-1,'steepener':shock(np.interp(t,[0,2,30],[-.005,-.005,.01]))/dirty-1,'flattener':shock(np.interp(t,[0,2,30],[.005,.005,-.01]))/dirty-1,'curvature':shock(np.interp(t,[0,5,10,30],[0,.01,.01,0]))/dirty-1}}


def holding_return(p0,p1,cash):
    if not np.isfinite([p0,p1,cash]).all() or p0<=0 or p1<0 or cash<0:raise ValueError('Invalid holding-period inputs')
    return (p1+cash)/p0-1


def ladder(candidates,settlement,capital,liabilities,cap=.25,cost_bps=10.,curve=None,mode='cashflow',duration_target=None,duration_tolerance=.25,max_dv01=None):
    """LP: funded nominal ladder with no borrowing; explicit unmatched liabilities.

    Cash collected in yearly buckets is carried at zero interest. Cost includes
    half of indicative quoted spread plus configured bps. Not executable quotes.
    """
    if not candidates or not 0<capital or not 0<cap<=1 or not 0<=cost_bps<=200 or not liabilities or any(not np.isfinite(v) or v<=0 for _,v in liabilities):raise ValueError('Invalid ladder inputs')
    dates=[d for d,_ in liabilities];amount=np.array([v for _,v in liabilities]);n=len(candidates);m=len(dates)
    if dates!=sorted(set(dates)) or dates[0]<=settlement:raise ValueError('Liability dates must be strictly increasing and future')
    price=np.array([q['indexed_dirty_per_100']*(1+cost_bps/10000)+q['spread_per_100']/2 for q in candidates]);matrix=np.array([[sum(v for d,v,_ in q['flows'] if d<=end) for q in candidates] for end in dates]);cum=np.cumsum(amount)
    if mode=='cashflow':
        # Cash left over plus receipts must cover cumulative liabilities.
        A=np.c_[price[None,:]-matrix,-np.eye(m)];bounds=[(0,capital*cap/p) for p in price]+[(0,None)]*m
        obj=np.r_[price/capital*1e-5,np.ones(m)/capital];b=np.r_[capital-cum,capital]
        A=np.r_[A,np.r_[price,np.zeros(m)][None,:]]
    elif mode in ('key_rate','combined'):
        if curve is None:raise ValueError('LDI requires nominal curve')
        t=np.array([(d-settlement).days/365.25 for d in dates]);pv=amount*discount(curve,t);target=np.array([np.sum(pv*t*np.interp(t,KEYS,np.eye(len(KEYS))[i]))*.0001 for i in range(len(KEYS))]);exposure=np.array([[q['key_rate_dv01'][str(k)] for q in candidates] for k in KEYS]);scale=np.maximum(abs(target),capital*.00001);a=exposure/scale[:,None];g=target/scale;k=len(KEYS)
        # Minimize normalized absolute key-rate dollar mismatch, fully funded.
        A=np.r_[np.c_[a,-np.eye(k)],np.c_[-a,-np.eye(k)],np.r_[price,np.zeros(k)][None,:]];b=np.r_[g,-g,capital];obj=np.r_[price/capital*1e-5,np.ones(k)];bounds=[(0,capital*cap/p) for p in price]+[(0,None)]*k
        if mode=='combined':
            # Require zero cumulative cash shortfall, then minimize key-rate mismatch.
            A=np.r_[A,np.c_[price[None,:]-matrix,np.zeros((m,k))]];b=np.r_[b,capital-cum]
    else:raise ValueError('Unknown ladder mode')
    duration=np.array([q['modified_duration']*q['indexed_dirty_per_100']/capital for q in candidates]);dv01=np.array([q['dv01_per_100'] for q in candidates]);padding=np.zeros(len(obj)-n)
    if duration_target is not None:
        A=np.r_[A,np.r_[duration,padding][None,:],np.r_[-duration,padding][None,:]];b=np.r_[b,duration_target+duration_tolerance,-max(0,duration_target-duration_tolerance)]
    if max_dv01 is not None:A=np.r_[A,np.r_[dv01,padding][None,:]];b=np.r_[b,max_dv01]
    res=linprog(obj,A_ub=A,b_ub=b,bounds=bounds,method='highs')
    if not res.success:raise ValueError('Ladder linear program infeasible')
    qty=res.x[:n];spent=float(price@qty);cash=capital-spent;received=matrix@qty
    # Uninvested cash is a real funding resource (conservative zero interest).
    available=received+cash;out={'status':'computed','capital':capital,'invested_with_cost':spent,'residual_cash':cash,'coverage':[{'date':str(d),'cumulative_liability':float(l),'available_cash':float(a),'shortfall':float(max(l-a,0))} for d,l,a in zip(dates,cum,available)],'holdings':[{'cusip':q['cusip'],'face':float(x*100),'cost':float(x*p),'weight':float(x*p/capital)} for q,x,p in zip(candidates,qty,price) if x>1e-8],'dv01':float(sum(q['dv01_per_100']*x for q,x in zip(candidates,qty))),'duration':float(sum(q['modified_duration']*x*q['indexed_dirty_per_100'] for q,x in zip(candidates,qty))/capital),'transaction_cost_estimate':float(sum(x*(p-q['indexed_dirty_per_100']) for q,x,p in zip(candidates,qty,price)))}
    if mode in ('key_rate','combined'):out['key_rate_matching']=[{'tenor':float(k),'asset_dv01':float(a),'liability_dv01':float(l),'gap':float(a-l)} for k,a,l in zip(KEYS,exposure@qty,target)]
    return out
