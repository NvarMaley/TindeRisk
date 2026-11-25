"""Robust, resampled, distributionally robust and growth/entropy objectives."""
from time import perf_counter
import numpy as np
from scipy.optimize import minimize,brentq
from sklearn.covariance import LedoitWolf
from riskmatch.optimization.mean_variance import MeanVariance,Constraints
from riskmatch.optimization.hierarchical import proportional_cap

VERSION='advanced-v2'


def block_draws(n,draws,block=3,seed=17):
    if n<block or draws<1 or block<1:raise ValueError('Invalid block bootstrap')
    rng=np.random.default_rng(seed);starts=rng.integers(0,n-block+1,(draws,(n+block-1)//block));return (starts[:,:,None]+np.arange(block)).reshape(draws,-1)[:,:n]


def fit(x):
    lw=LedoitWolf().fit(x);return x.mean(0)*12,lw.covariance_*12,float(lw.shrinkage_)


def uncertainty(x,draws,scale=1.,seed=17):
    """Box mean half-width and spectral covariance ball calibrated from train blocks."""
    x=np.asarray(x,float);mu,cov,_=fit(x);means=[];covs=[];radii=[]
    for ix in block_draws(len(x),draws,seed=seed):
        m,s,_=fit(x[ix]);means.append(m);covs.append(s);radii.append(float(np.max(np.abs(np.linalg.eigvalsh(s-cov)))))
    means=np.array(means);half=scale*np.quantile(np.abs(means-mu),.9,axis=0);radius=float(scale*np.quantile(radii,.9));return mu,cov,half,radius,means,covs


def quadratic(mu,cov,upper,lam,penalty,reference,warm=None):
    model=MeanVariance(mu,cov,0.,Constraints(np.zeros(len(mu)),np.asarray(upper),previous=np.asarray(reference),turnover_penalty=penalty));return model.solve(return_weight=1.,variance_weight=lam,warm=warm)


def robust_utility(mu,cov,half,radius,upper,lam,penalty,reference):
    if radius<0 or np.any(np.asarray(half)<0):raise ValueError('Negative uncertainty radius')
    # Worst-case mean for funded nonnegative weights; spectral ball worst variance.
    result=quadratic(np.asarray(mu)-half,np.asarray(cov)+radius*np.eye(len(mu)),upper,lam,penalty,reference)
    if result.get('status')=='optimal':
        w=np.asarray(result['weights']);result|={'worst_expected_return':float((mu-half)@w),'worst_variance':float(w@(cov+radius*np.eye(len(mu)))@w),'mean_uncertainty_penalty':float(half@w),'covariance_uncertainty_penalty':float(radius*(w@w))}
    return result


def resampled_utility(means,covs,upper,lam,penalty,reference):
    rows=[];failed=0;warm=None;iterations=[];gaps=[];start=perf_counter()
    for mu,cov in zip(means,covs):
        r=quadratic(mu,cov,upper,lam,penalty,reference,warm)
        if r.get('status')!='optimal':failed+=1;continue
        warm=np.asarray(r['weights']);rows.append(warm);iterations.append(r['iterations']);gaps.append(r['optimality_gap'])
    if failed or not rows:return {'status':'unconverged','reason':'At least one resampled solution not certified; no selective aggregation','failed_draws':failed,'successful_draws':len(rows)}
    array=np.asarray(rows);w=array.mean(0);res=max(abs(w.sum()-1),float(np.maximum(w-upper,0).max()),float(np.maximum(-w,0).max()))
    return {'status':'aggregated_feasible' if res<2e-7 else 'unconverged','weights':w.tolist(),'solver':'block-resampled certified utility average','draws':len(rows),'failed_draws':0,'residual':float(res),'weight_std':array.std(0).tolist(),'mean_draw_distance':float(np.abs(array-w).sum(1).mean()/2),'max_draw_gap':float(max(gaps)),'iterations':int(sum(iterations)),'runtime_seconds':perf_counter()-start}


def convex_smooth(fun,grad,upper,reference,penalty,*,lipschitz=1.,linear=None,warm=None):
    """Convex objective + half-L1 turnover, projected proximal gradient / SLSQP."""
    u=np.asarray(upper,float);n=len(u);ref=np.asarray(reference,float);start=perf_counter();c=Constraints(np.zeros(n),u,linear=linear or [],previous=ref,turnover_penalty=penalty);p=MeanVariance(np.zeros(n),np.eye(n),0,c)
    if not p.feasible:return {'status':'infeasible','reason':p.feasibility.message}
    def val(w):return fun(w)+penalty*np.abs(w-ref).sum()/2
    if p.simple:
        w=p._project(ref if warm is None else np.asarray(warm));z=w.copy();t=1.;L=max(lipschitz,1e-8);message='Iteration limit'
        for i in range(1,2501):
            if not np.isfinite(fun(z)):z=w.copy();t=1.
            g=grad(z);fz=fun(z)
            for _ in range(50):
                q=p._project(z-g/L,threshold=penalty/(2*L));d=q-z;fq=fun(q)
                if np.isfinite(fq) and fq<=fz+g@d+.5*L*(d@d)+1e-12:break
                L*=2
            else:return {'status':'unconverged','reason':'Convex backtracking failed'}
            if val(q)>val(w)+1e-12:z=w.copy();t=1.;continue
            if np.max(abs(q-w))<1e-9 and i>5:w=q;message='Projected iterate tolerance';break
            tn=(1+np.sqrt(1+4*t*t))/2;z=q+(t-1)/tn*(q-w);w=q;t=tn;L=max(L*.98,1e-8)
        solver='proximal FISTA'
    else:
        def f(a):return fun(a[:n])+(penalty*a[-n:].sum()/2 if p.turn_aux else 0.)
        def g(a):
            r=np.pad(grad(a[:n]),(0,p.dim-n));
            if p.turn_aux:r[-n:]=penalty/2
            return r
        cons=[{'type':'eq','fun':lambda z:p.eq@z-1,'jac':lambda z:p.eq},{'type':'ineq','fun':lambda z:p.b-p.A@z,'jac':lambda z:-p.A}];r=minimize(f,p.feasibility.x,jac=g,bounds=p.bounds,constraints=cons,method='SLSQP',options={'ftol':1e-12,'maxiter':500});w=r.x[:n];i=int(r.nit);solver='SLSQP linear-constrained';message=str(r.message)
    g=grad(w);oracle=p.lp(g,penalty=penalty);gap=None
    if oracle.success:
        z=oracle.x[:n];gap=max(0.,float(g@(w-z)+penalty*(np.abs(w-ref).sum()-np.abs(z-ref).sum())/2))
    residual=max(p.diagnostics(w)['residuals'].values());ok=gap is not None and gap<=2e-6 and residual<2e-7 and np.isfinite(val(w));return {'status':'optimal' if ok else 'unconverged','weights':w.tolist(),'objective':float(val(w)) if np.isfinite(val(w)) else None,'optimality_gap':gap,'residual':float(residual),'solver':solver,'iterations':i,'message':message,'runtime_seconds':perf_counter()-start}


def wasserstein_utility(mu,cov,epsilon,upper,lam,penalty,reference):
    """W1 Euclidean ambiguity on mean return; nominal covariance risk term."""
    if not np.isfinite(epsilon) or epsilon<0:raise ValueError('Invalid Wasserstein radius')
    mu=np.asarray(mu);cov=np.asarray(cov)
    f=lambda w:.5*lam*float(w@cov@w)-float(mu@w)+epsilon*np.linalg.norm(w)
    g=lambda w:lam*(cov@w)-mu+epsilon*w/max(np.linalg.norm(w),1e-12)
    r=convex_smooth(f,g,upper,reference,penalty,lipschitz=lam*float(np.linalg.eigvalsh(cov)[-1])+epsilon*np.sqrt(len(mu)))
    if r['status']=='optimal':w=np.asarray(r['weights']);r|={'worst_expected_return':float(mu@w-epsilon*np.linalg.norm(w)),'wasserstein_penalty':float(epsilon*np.linalg.norm(w)),'radius':epsilon}
    return r


def kelly(x,upper,penalty,reference,wealth_floor=.01):
    x=np.asarray(x,float);u=np.asarray(upper,float)
    if x.ndim!=2 or x.shape[1]!=len(u) or not np.isfinite(x).all() or np.any(x< -1) or not 0<wealth_floor<1:raise ValueError('Invalid Kelly scenarios or floor')
    # Only include wealth constraints that can bind over the capped simplex.
    linear=[]
    for i,row in enumerate(x):
        order=np.argsort(row);remaining=1.;worst=0.
        for j in order:
            take=min(remaining,u[j]);worst+=take*row[j];remaining-=take
            if remaining<=1e-12:break
        if 1+worst<wealth_floor:linear.append((f'wealth_scenario_{i}',row,wealth_floor-1,float(row.max()+1)))
    def f(w):
        v=1+x@w;return -12*float(np.mean(np.log(v))) if np.all(v>0) else float('inf')
    def g(w):return -12*x.T@(1/np.maximum(1+x@w,1e-12))/len(x)
    r=convex_smooth(f,g,u,reference,penalty,lipschitz=12*float(np.linalg.eigvalsh(x.T@x/len(x))[-1]),linear=linear)
    if r['status']=='optimal':
        w=np.asarray(r['weights']);wealth=1+x@w;r|={'minimum_scenario_wealth':float(wealth.min()),'annual_log_growth':float(12*np.log(wealth).mean()),'wealth_floor':wealth_floor,'wealth_constraints':len(linear)}
        if wealth.min()<wealth_floor-2e-7:r['status']='unconverged'
    return r


def entropy_utility(mu,cov,eta,upper,lam,penalty,reference):
    if not np.isfinite(eta) or eta<0:raise ValueError('Invalid entropy weight')
    if eta==0:return quadratic(mu,cov,upper,lam,penalty,reference)
    # Entropic mirror-prox step: exact entropy + L1 prox, and box-budget dual root.
    start=perf_counter();mu=np.asarray(mu);cov=np.asarray(cov);u=np.asarray(upper);ref=np.asarray(reference);n=len(u);active=u>0;ids=np.flatnonzero(active)
    if u.sum()<1-1e-10:return {'status':'infeasible','reason':'Insufficient funded capacity'}
    w,_=proportional_cap(np.ones(n)/n,u);p=MeanVariance(np.zeros(n),np.eye(n),0,Constraints(np.zeros(n),u,previous=ref,turnover_penalty=penalty))
    def smooth(w):return .5*lam*float(w@cov@w)-float(mu@w)
    def g(w):return lam*(cov@w)-mu
    def objective(w):return smooth(w)+eta*float(np.sum(w[active]*np.log(np.maximum(w[active],1e-300))))+penalty*np.abs(w-ref).sum()/2
    if abs(u.sum()-1)<1e-10:
        w=u/u.sum();return {'status':'optimal','weights':w.tolist(),'objective':float(objective(w)),'optimality_gap':0.,'residual':float(np.maximum(w-u,0).max()),'entropy':float(-np.sum(w[w>0]*np.log(w[w>0]))),'entropy_weight':eta,'solver':'unique feasible capped vector','iterations':0,'runtime_seconds':perf_counter()-start}
    step=1/max(lam*float(np.linalg.eigvalsh(cov)[-1]),.01);gap=None;message='Iteration limit'
    for i in range(1,4001):
        gradient=g(w);old=w[active];logold=np.log(np.maximum(old,1e-300));a=u[active];b=ref[active]
        for _ in range(40):
            A=eta+1/step;z=logold/step-gradient[active]-eta
            def candidate(t):
                plus=np.exp(np.clip((z-t-penalty/2)/A,-690,690));minus=np.exp(np.clip((z-t+penalty/2)/A,-690,690));return np.minimum(np.where(plus>b,plus,np.where(minus<b,minus,b)),a)
            lo=float(np.min(z-A*np.log(np.maximum(a,1e-300)))-penalty-2*A);hi=float(np.max(z)-A*np.log(1e-15)+penalty+2*A)
            q=np.zeros(n);q[active]=candidate(brentq(lambda t:candidate(t).sum()-1,lo,hi,xtol=1e-12));d=q-w
            kl=float(np.sum(q[active]*(np.log(np.maximum(q[active],1e-300))-logold)-q[active]+old))
            if smooth(q)<=smooth(w)+gradient@d+max(kl,0.)/step+1e-12:break
            step/=2
        else:return {'status':'unconverged','reason':'Entropy mirror backtracking failed'}
        w=q;step=min(step*1.15,1e5)
        if i%10==0 or np.max(abs(d))<1e-10:
            fullgrad=g(w);fullgrad[active]+=eta*(np.log(np.maximum(w[active],1e-300))+1);oracle=p.lp(fullgrad,penalty=penalty)
            if oracle.success:
                z=oracle.x[:n];gap=max(0.,float(fullgrad@(w-z)+penalty*(np.abs(w-ref).sum()-np.abs(z-ref).sum())/2))
                if gap<2e-6:message='Entropy LP dual gap certified';break
    residual=max(abs(w.sum()-1),float(np.maximum(w-u,0).max()),float(np.maximum(-w,0).max()));return {'status':'optimal' if gap is not None and gap<2e-6 and residual<2e-7 else 'unconverged','weights':w.tolist(),'objective':float(objective(w)),'optimality_gap':gap,'residual':float(residual),'entropy':float(-np.sum(w[w>0]*np.log(w[w>0]))),'entropy_weight':eta,'solver':'exact entropy/L1 mirror-prox','iterations':i,'message':message,'runtime_seconds':perf_counter()-start}
