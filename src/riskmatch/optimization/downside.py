"""Downside and benchmark objectives on monthly scenario returns, funded long-only."""
import numpy as np
from scipy.optimize import linprog,brentq
from scipy import sparse
from riskmatch.optimization.mean_variance import MeanVariance,Constraints

VERSION='downside-v2'


def validate(x,upper,prob=None):
    x=np.asarray(x,float);u=np.asarray(upper,float)
    if x.ndim!=2 or len(x)<2 or x.shape[1]!=len(u) or not np.isfinite(x).all() or np.any(x< -1) or not np.isfinite(u).all() or np.any(u<0) or u.sum()<1-1e-10:raise ValueError('Invalid or infeasible scenario matrix/caps')
    p=np.ones(len(x))/len(x) if prob is None else np.asarray(prob,float)
    if p.shape!=(len(x),) or not np.isfinite(p).all() or np.any(p<=0) or not np.isclose(p.sum(),1):raise ValueError('Scenario probabilities must be positive and sum to one')
    return x,u,p


def tail(loss,prob,alpha):
    l=np.asarray(loss,float);p=np.asarray(prob,float);order=np.argsort(l);l=l[order];p=p[order];cum=np.cumsum(p);i=min(len(l)-1,int(np.searchsorted(cum,alpha,side='left')));mass=np.maximum(0,np.minimum(p,cum-alpha));return float(l[i]),float(mass@l/(1-alpha))


def stats(r,mar=0.,benchmark=None,alpha=.95,prob=None):
    r=np.asarray(r,float);p=np.ones(len(r))/len(r) if prob is None else np.asarray(prob,float);e=r-mar;d=np.maximum(-e,0);g=np.maximum(e,0);den=float(np.sqrt(p@(d*d)));loss=float(p@d);gain=float(p@g);var,es=tail(-r,p,alpha);cum=np.r_[1.,np.cumprod(1+r)];dd=cum/np.maximum.accumulate(cum)-1
    result={'period_mean':float(p@r),'var':var,'cvar':es,'downside_deviation':den,'sortino':float((p@e)/den*np.sqrt(12)) if den>1e-12 else None,'omega':gain/loss if loss>1e-12 else None,'downside_zero':loss<=1e-12,'maximum_drawdown':float(-dd.min()),'drawdown':dd[1:].tolist(),'wealth':cum[1:].tolist()}
    if benchmark is not None:
        active=r-np.asarray(benchmark,float);am=float(p@active);te=float(np.sqrt(p@((active-am)**2)*12));result|={'active_annual_mean':am*12,'tracking_error':te,'information_ratio':am*12/te if te>1e-12 else None}
    return result


def lp_result(opt,n,upper,objective_name):
    if not opt.success:return {'status':'infeasible' if opt.status==2 else 'unbounded' if opt.status==3 else 'unconverged','reason':str(opt.message),'solver':'HiGHS LP'}
    w=np.asarray(opt.x[:n]);res=max(abs(w.sum()-1),float(np.maximum(-w,0).max()),float(np.maximum(w-upper,0).max()));return {'status':'optimal' if res<2e-7 else 'unconverged','weights':w.tolist(),'objective':float(opt.fun),'objective_name':objective_name,'residual':float(res),'solver':'HiGHS LP','iterations':int(opt.nit),'message':str(opt.message)}


def cvar(x,upper,alpha=.95,prob=None,target=None):
    x,u,p=validate(x,upper,prob);m,n=x.shape
    if not .5<=alpha<1:raise ValueError('Invalid CVaR confidence')
    # loss - z - slack <= 0; z unrestricted. Exact fractional discrete tails.
    A=sparse.hstack([-sparse.csr_matrix(x),-np.ones((m,1)),-sparse.eye(m)],format='csr');b=np.zeros(m)
    if target is not None:A=sparse.vstack([A,np.r_[-p@x,np.zeros(m+1)]]);b=np.r_[b,-target]
    obj=np.r_[np.zeros(n),1,p/(1-alpha)];eq=np.r_[np.ones(n),np.zeros(m+1)][None,:];opt=linprog(obj,A_ub=A,b_ub=b,A_eq=eq,b_eq=[1],bounds=[(0,float(v)) for v in u]+[(None,None)]+[(0,None)]*m,method='highs');r=lp_result(opt,n,u,'CVaR')
    if r['status']=='optimal':
        w=np.asarray(r['weights']);v,e=tail(-x@w,p,alpha);r|={'z':float(opt.x[n]),'cvar':e,'var':v,'objective_error':abs(e-opt.fun),'target':target}
        if abs(e-opt.fun)>2e-7 or target is not None and p@(x@w)<target-2e-7:r['status']='unconverged'
    return r


def cdar(x,upper,alpha=.95):
    """Conditional drawdown at risk of additive constant-weight P&L, not compounded NAV."""
    x,u,p=validate(x,upper);m,n=x.shape;cum=np.cumsum(x,axis=0);I=sparse.eye(m);zero=sparse.csr_matrix((m,m));Z=sparse.csr_matrix((m,n));col=sparse.csr_matrix((m,1));
    # vars weights, running peaks >=0, z>=0, tail shortfalls >=0
    a1=sparse.hstack([sparse.csr_matrix(cum),-I,col,zero]);diff=sparse.diags([np.ones(m-1),-np.ones(m-1)],[0,1],shape=(m-1,m));a2=sparse.hstack([sparse.csr_matrix((m-1,n)),diff,sparse.csr_matrix((m-1,1+m))]);a3=sparse.hstack([-sparse.csr_matrix(cum),I,-np.ones((m,1)),-I]);A=sparse.vstack([a1,a2,a3],format='csr')
    obj=np.r_[np.zeros(n+m),1,p/(1-alpha)];eq=np.r_[np.ones(n),np.zeros(2*m+1)][None,:];opt=linprog(obj,A_ub=A,b_ub=np.zeros(3*m-1),A_eq=eq,b_eq=[1],bounds=[(0,float(v)) for v in u]+[(0,None)]*(2*m+1),method='highs');r=lp_result(opt,n,u,'additive_CDAR')
    if r['status']=='optimal':
        path=np.r_[0.,cum@np.asarray(r['weights'])];dd=np.maximum.accumulate(path)[1:]-path[1:];_,v=tail(dd,p,alpha);r|={'cdar':v,'additive_drawdown':dd.tolist(),'objective_error':abs(v-opt.fun)}
        if abs(v-opt.fun)>2e-7:r['status']='unconverged'
    return r


def ratio_precheck(x,u,p,mar):
    d=x-mar;mu=p@d;n=len(u);bounds=list(zip(np.zeros(n),u));eq=np.ones((1,n));mx=linprog(-mu,A_eq=eq,b_eq=[1],bounds=bounds,method='highs')
    if not mx.success:return d,mu,{'status':'infeasible','reason':str(mx.message)}
    if -mx.fun<=1e-10:return d,mu,{'status':'unavailable','reason':'No positive feasible excess above MAR'}
    zero=linprog(-mu,A_ub=-d,b_ub=np.zeros(len(d)),A_eq=eq,b_eq=[1],bounds=bounds,method='highs')
    if zero.success and -zero.fun>1e-10:return d,mu,{'status':'zero_downside','reason':'Positive excess with zero observed downside; ratio undefined; no infinity ranking','weights':zero.x.tolist()}
    return d,mu,None


def capped_vertices(upper):
    """Exact vertices for a small long-only capped simplex; at most one free coordinate."""
    u=np.asarray(upper,float);n=len(u)
    if n>12:return
    for mask in range(1<<n):
        w=u*np.array([(mask>>i)&1 for i in range(n)]);remainder=1-w.sum()
        if remainder< -1e-10:continue
        if abs(remainder)<1e-10:yield w;continue
        for i in range(n):
            if not (mask>>i)&1 and remainder<=u[i]+1e-10:
                v=w.copy();v[i]=remainder;yield v


def negative_ratio(upper,mean,denominator,name):
    """For nonpositive excess, max signed ratio occurs at a vertex (homogeneous norm / loss)."""
    if len(upper)>12:return {'status':'unavailable','reason':'No positive excess; exact signed vertex search limited to 12 assets'}
    best=None;count=0
    for w in capped_vertices(upper):
        count+=1;e=float(mean@w);d=float(denominator(w))
        if d<=1e-12:continue
        value=e/d
        if best is None or value>best[0]:best=(value,w.copy())
    if best is None:return {'status':'unavailable','reason':'No finite ratio on feasible vertices (zero denominator)'}
    val,w=best;return {'status':'optimal','weights':w.tolist(),'solver':'exact_signed_vertex_search','vertices_examined':count,'signed_nonpositive_excess':True,'ratio_raw':val,'objective_name':name}


def omega(x,upper,mar=0.,prob=None):
    x,u,p=validate(x,upper,prob);d,mu,status=ratio_precheck(x,u,p,mar)
    if status:
        if status['status']=='unavailable' and 'positive' in status.get('reason',''):
            r=negative_ratio(u,mu,lambda w:p@np.maximum(-d@w,0),'omega')
            if 'ratio_raw'in r:r['omega']=1+r['ratio_raw']
            return r
        return status
    m,n=d.shape
    # Charnes-Cooper: y=t*w, t=1/E[shortfall]; maximize active mean over normalized downside.
    # sum y=t, y_i<=u_i*t, d*y+v>=0; E[v]=1. Tight for positive objective.
    A=sparse.vstack([sparse.hstack([sparse.eye(n),sparse.csr_matrix((n,m)),-u[:,None]]),sparse.hstack([-sparse.csr_matrix(d),-sparse.eye(m),sparse.csr_matrix((m,1))])]);eq=np.vstack([np.r_[np.ones(n),np.zeros(m),-1],np.r_[np.zeros(n),p,0]]);obj=np.r_[-mu,np.zeros(m+1)];opt=linprog(obj,A_ub=A,b_ub=np.zeros(n+m),A_eq=eq,b_eq=[0,1],bounds=[(0,None)]*(n+m+1),method='highs')
    if not opt.success:return {'status':'unconverged','reason':str(opt.message)}
    t=opt.x[-1];w=opt.x[:n]/t;r=stats(x@w,mar,prob=p);res=max(abs(w.sum()-1),float(np.maximum(w-u,0).max()),float(np.maximum(-w,0).max()));err=abs(r['omega']-(1-opt.fun)) if r['omega'] is not None else None
    return {'status':'optimal' if res<2e-7 and err is not None and err<2e-6 else 'unconverged','weights':w.tolist(),'omega':r['omega'],'objective_error':err,'residual':float(res),'solver':'HiGHS homogeneous LP','iterations':int(opt.nit)}


def sortino(x,upper,mar=0.,prob=None):
    x,u,p=validate(x,upper,prob);d,mu,status=ratio_precheck(x,u,p,mar)
    if status:
        if status['status']=='unavailable' and 'positive'in status.get('reason',''):
            r=negative_ratio(u,mu,lambda w:np.sqrt(p@np.minimum(d@w,0)**2),'sortino')
            if 'ratio_raw'in r:r['sortino']=r['ratio_raw']*np.sqrt(12)
            return r
        return status
    n=len(u);L=max(1e-12,float(np.linalg.eigvalsh((d.T*p)@d)[-1]));projector=MeanVariance(mu,np.eye(n)*.01,0,Constraints(np.zeros(n),u));
    def variance(w):return float(p@np.minimum(d@w,0)**2)
    def gradient(w):return d.T@(p*np.minimum(d@w,0))
    def linear_minimum(objective):
        # On a funded, capped simplex, fill the least costly positions first.
        order = np.argsort(objective, kind="stable")
        caps = u[order]
        remaining = 1. - np.r_[0., np.cumsum(caps[:-1])]
        weights = np.empty(n)
        weights[order] = np.clip(remaining, 0., caps)
        return weights

    warm = linear_minimum(-mu)
    best = None
    def sub(k):
        nonlocal warm,best
        w=projector._project(warm);z=w.copy();t=1.;last=0
        for i in range(1,3501):
            q=projector._project(z-(gradient(z)-k*mu)/L)
            if np.max(abs(q-w))<2e-9 and i>5:w=q;break
            tn=(1+np.sqrt(1+4*t*t))/2;z=q+(t-1)/tn*(q-w);w=q;t=tn
        g = gradient(w) - k * mu
        gap = max(0., float(g @ (w - linear_minimum(g))))
        v = variance(w)
        e = float(mu @ w)
        res = k * e - v
        warm = w
        if e>0 and gap<2e-7 and (best is None or abs(res)<best[0]):best=(abs(res),w.copy(),v,e,gap,i)
        return res
    lo=0.;hi=max(variance(warm)/max(float(mu@warm),1e-10),1e-6);a=sub(lo);b=sub(hi)
    for _ in range(25):
        if b>=0:break
        hi*=2;b=sub(hi)
    try:
        if a<0 and b>=0:sub(brentq(sub,lo,hi,xtol=1e-10,maxiter=40))
    except ValueError:pass
    if best is None or best[0]>max(1e-8,1e-5*best[2]):return {'status':'unconverged','reason':'Sortino tangency not certified'}
    residual,w,v,e,gap,it=best;return {'status':'optimal','weights':w.tolist(),'sortino':float(e/np.sqrt(v)*np.sqrt(12)) if v>1e-20 else None,'tangency_residual':residual,'optimality_gap':gap,'solver':'convex downside QP tangency / projected FISTA','iterations':it}


def benchmark_models(x,upper,benchmark_weights,cov):
    x,u,p=validate(x,upper);b=np.asarray(benchmark_weights,float);n=len(u)
    if b.shape!=(n,) or np.any(b<0) or not np.isclose(b.sum(),1):raise ValueError('Invalid benchmark identity/weights')
    A=np.eye(n)-b[:,None];active=A.T@np.asarray(cov)@A;mu=(x.mean(0)-x.mean(0)@b)*12;engine=MeanVariance(mu,active,0.,Constraints(np.zeros(n),u));te=engine.solve(penalty=0.);ir=engine.max_sharpe((te,[]))
    if ir.get('status')=='unavailable' and 'positive' in ir.get('reason',''):
        ir=negative_ratio(u,mu,lambda w:np.sqrt(max(0,float(w@active@w))),'information_ratio')
        if 'weights'in ir:ir|=engine.diagnostics(np.asarray(ir['weights']))
    return te,ir
