"""Long-only risk budgeting, hierarchy and diversification research."""
import numpy as np
from scipy.cluster.hierarchy import linkage,leaves_list,cut_tree,to_tree
from scipy.spatial.distance import squareform
from scipy.optimize import minimize,brentq
from riskmatch.optimization.mean_variance import MeanVariance,Constraints

VERSION='hierarchical-v2'


def covariance(cov):
    c=np.asarray(cov,float)
    if c.ndim!=2 or c.shape[0]!=c.shape[1] or len(c)<1 or not np.isfinite(c).all() or not np.allclose(c,c.T,rtol=1e-8,atol=1e-12):raise ValueError('Invalid covariance')
    c=(c+c.T)/2;e=np.linalg.eigvalsh(c)
    if e.min()<-max(1e-10,abs(e.max())*1e-9):raise ValueError('Non-PSD covariance')
    c+=np.eye(len(c))*max(0.,-e.min());return c


def risk_contributions(cov,weights):
    c=np.asarray(cov,float);w=np.asarray(weights,float)
    if w.shape!=(len(c),) or not np.isfinite(w).all():raise ValueError('Invalid weights')
    var=float(w@c@w);vol=float(np.sqrt(max(var,0)))
    if vol<1e-12:return {'volatility':vol,'marginal':None,'contributions':None,'shares':None,'sum_residual':None}
    mr=c@w/vol;rc=w*mr;return {'volatility':vol,'marginal':mr.tolist(),'contributions':rc.tolist(),'shares':(rc/vol).tolist(),'sum_residual':float(abs(rc.sum()-vol))}


def risk_budget(cov,budgets=None,upper=None):
    """Convex log-budget problem with positive variables, normalized afterward."""
    c=covariance(cov);n=len(c);b=np.ones(n)/n if budgets is None else np.asarray(budgets,float)
    if b.shape!=(n,) or not np.isfinite(b).all() or np.any(b<=0) or not np.isclose(b.sum(),1,atol=1e-9):raise ValueError('Strictly positive budgets must sum to one')
    sigma=np.sqrt(np.diag(c))
    if np.any(sigma<=1e-12):return {'status':'unavailable','reason':'Zero standalone risk cannot support positive risk budget'}
    # Standardize variables for conditioning; x is unnormalized monetary allocation.
    corr=c/sigma[:,None]/sigma[None,:];z0=np.sqrt(b)
    def f(z):return .5*float(z@corr@z)-float(b@np.log(z))
    def g(z):return corr@z-b/z
    opt=minimize(f,z0,jac=g,bounds=[(1e-12,None)]*n,method='L-BFGS-B',options={'ftol':1e-14,'gtol':1e-10,'maxiter':3000,'maxls':50})
    w=opt.x/sigma;w/=w.sum();r=risk_contributions(c,w)
    if r['shares'] is None:return {'status':'unavailable','reason':'Near-zero portfolio volatility; risk shares undefined'}
    gap=max(abs(np.asarray(r['shares'])-b))
    out={'status':'optimal' if gap<2e-5 else 'unconverged','weights':w,'budget_error':float(gap),'iterations':int(opt.nit),'solver':'convex_log_budget_LBFGSB','message':str(opt.message),'budgets':b.tolist(),'raw_max_weight':float(w.max())}
    if upper is None or out['status']!='optimal':return out
    upper=np.asarray(upper,float)
    if upper.shape!=(n,) or not np.isfinite(upper).all() or np.any(upper<=0) or upper.sum()<1-1e-10:raise ValueError('Infeasible positive risk-budget caps')
    if np.all(w<=upper+1e-9):return out
    # Convex homogeneous cap cone: x_i <= u_i sum(x). For an active set A,
    # eliminate x_A = u_A/(1-sum u_A) * sum(x_F). Remaining log problem convex.
    raw=w.copy();w,_=proportional_cap(w,upper);active=set(np.flatnonzero(raw>upper+1e-9));total_iter=int(opt.nit)
    if abs(upper.sum()-1)<1e-10:
        w=upper/upper.sum();return out|{'status':'constrained_optimal','weights':w,'budget_error':describe(c,w,b)['budget_error'],'raw_max_weight':float(raw.max()),'cap_binding_count':n,'kkt_residual':0.,'solver':'unique_feasible_cap_vector'}
    for _ in range(2*n+10):
        A=np.array(sorted(active),int);F=np.array([i for i in range(n) if i not in active],int)
        if not len(F) or upper[A].sum()>=1-1e-12:
            if not active:break
            active.remove(max(active,key=lambda i:upper[i]));continue
        B=np.zeros((n,len(F)));B[F,np.arange(len(F))]=1
        if len(A):B[A,:]=(upper[A]/(1-upper[A].sum()))[:,None]
        sf=sigma[F];inverse=1/sf;M=(B.T@c@B)*inverse[:,None]*inverse[None,:];ba=float(b[A].sum());bf=b[F]
        z=np.maximum(w[F]*sf/max(risk_contributions(c,w)['volatility'],1e-12),1e-9)
        def f(u):return .5*float(u@M@u)-float(bf@np.log(u))-ba*np.log(u@inverse)
        def g(u):return M@u-bf/u-ba*inverse/(u@inverse)
        q=minimize(f,z,jac=g,bounds=[(1e-12,None)]*len(F),method='L-BFGS-B',options={'ftol':1e-15,'gtol':1e-10,'maxiter':3000,'maxls':50});total_iter+=int(q.nit)
        w=B@(q.x*inverse);w/=w.sum();violation=w-upper
        if violation.max()>2e-8:active.add(int(np.argmax(violation)));continue
        var=float(w@c@w);grad=c@w/var-b/w;lam=float(np.mean(grad[F]));release=[i for i in A if grad[i]>lam+2e-5]
        if release:active.remove(max(release,key=lambda i:grad[i]-lam));continue
        kkt=max(float(np.max(abs(grad[F]-lam))),max([0.,*(float(grad[i]-lam) for i in A)]),max(0.,float(violation.max())))
        if kkt<2e-4:
            return out|{'status':'constrained_optimal','weights':w,'budget_error':describe(c,w,b)['budget_error'],'raw_max_weight':float(raw.max()),'iterations':total_iter,'cap_binding_count':len(A),'kkt_residual':kkt,'solver':'convex_homogeneous_active_set','message':'Constrained log-budget KKT checked; risk shares may differ from target'}
        break
    return out|{'status':'unconverged','reason':'Constrained log-budget KKT not certified','raw_max_weight':float(raw.max())}


def proportional_cap(w,upper):
    w=np.asarray(w,float);u=np.asarray(upper,float)
    if w.shape!=u.shape or np.any(w<0) or np.any(u<0) or not np.isfinite([w,u]).all() or u.sum()<1-1e-10:raise ValueError('Infeasible funded caps')
    if np.all(w<=u+1e-10):return w/w.sum(),False
    # Redistribute proportionally to uncapped weights. This is NOT an exact ERC/HRP solution.
    w=np.maximum(w,1e-15);hi=1.
    while np.minimum(w*hi,u).sum()<1-1e-12:hi*=2
    s=brentq(lambda k:np.minimum(w*k,u).sum()-1,0,hi,xtol=1e-12) if np.minimum(w*hi,u).sum()>1 else hi
    q=np.minimum(w*s,u);q/=q.sum();return q,True


def hierarchy(cov,method='average',ids=None):
    c=covariance(cov);n=len(c);sigma=np.sqrt(np.diag(c))
    if n<2 or np.any(sigma<=1e-12):raise ValueError('Hierarchy requires positive standalone risk')
    if method not in ('single','average','complete'):raise ValueError('Invalid linkage')
    if ids is not None and (len(ids)!=n or len(set(ids))!=n):raise ValueError('Duplicate asset identifiers')
    corr=np.clip(c/sigma[:,None]/sigma[None,:],-1,1);corr=(corr+corr.T)/2;corr[np.abs(corr-1)<1e-12]=1.;np.fill_diagonal(corr,1);dist=np.sqrt(np.maximum(0,(1-corr)/2));dist=(dist+dist.T)/2;np.fill_diagonal(dist,0)
    z=linkage(squareform(dist,checks=True),method=method,optimal_ordering=False);return {'linkage':z,'order':leaves_list(z),'distance':dist,'duplicate_pair_count':int((np.triu(dist<1e-8,1)).sum()),'method':method}


def inverse_variance(c):
    d=np.diag(c)
    if np.any(d<=1e-20):raise ValueError('Zero variance cluster')
    w=1/d;return w/w.sum()


def hrp(cov,tree):
    c=np.asarray(cov,float);w=np.ones(len(c));clusters=[list(tree['order'])]
    while clusters:
        nxt=[]
        for group in clusters:
            if len(group)<2:continue
            a,b=group[:len(group)//2],group[len(group)//2:];ca=c[np.ix_(a,a)];cb=c[np.ix_(b,b)];wa=inverse_variance(ca);wb=inverse_variance(cb);va=float(wa@ca@wa);vb=float(wb@cb@wb)
            alpha=vb/(va+vb) if va+vb>1e-20 else .5;w[a]*=alpha;w[b]*=1-alpha;nxt.extend([a,b])
        clusters=nxt
    return w/w.sum()


def herc(cov,tree,k,upper=None):
    """Two-level HERC variant: ERC within dendrogram-cut clusters and across cluster portfolios."""
    c=np.asarray(cov,float);n=len(c)
    if not isinstance(k,int) or not 2<=k<=n:raise ValueError('Invalid cluster count')
    labels=cut_tree(tree['linkage'],n_clusters=k).ravel();unique=np.unique(labels);B=np.zeros((n,len(unique)));inner=[]
    for j,label in enumerate(unique):
        ix=np.flatnonzero(labels==label);sub=c[np.ix_(ix,ix)];r=risk_budget(sub)
        if r['status']!='optimal':return {'status':'unconverged','reason':'Within-cluster risk budget not certified'}
        B[ix,j]=r['weights'];inner.append(float(r['budget_error']))
    cluster_cov=B.T@c@B;r=risk_budget(cluster_cov);raw=B@r['weights'] if r['status']=='optimal' else None
    if r['status']!='optimal':return {'status':r['status'],'reason':'Cluster risk budget not certified'}
    if upper is not None and np.any(raw>np.asarray(upper)+1e-9):
        u=np.asarray(upper);cu=np.array([min(1.,float(np.min(u[B[:,j]>0]/B[B[:,j]>0,j]))) for j in range(len(unique))]);
        if cu.sum()>=1-1e-10:
            r=risk_budget(cluster_cov,upper=cu)
            if r['status'] not in ('optimal','constrained_optimal'):return {'status':r['status'],'reason':'Constrained cluster risk budget not certified'}
        else:
            return {'status':'optimal','weights':raw/raw.sum(),'labels':labels,'cluster_budget_error':r['budget_error'],'max_inner_budget_error':max(inner),'variant':'two_level_cluster_ERC','raw_max_weight':float(raw.max()),'constraint_note':'Cluster caps infeasible with fixed inner allocations; proportional cap fallback required'}
    w=B@r['weights'];return {'status':r['status'],'weights':w/w.sum(),'labels':labels,'cluster_weights':r['weights'].tolist(),'cluster_risk_shares':risk_contributions(cluster_cov,r['weights'])['shares'],'cluster_budget_error':r['budget_error'],'max_inner_budget_error':max(inner),'variant':'two_level_cluster_ERC','raw_max_weight':float(raw.max()),'cluster_kkt_residual':r.get('kkt_residual')}


def maximum_diversification(cov,upper):
    c=covariance(cov);s=np.sqrt(np.diag(c));n=len(c)
    if np.any(s<=1e-12):return {'status':'unavailable','reason':'Zero standalone volatility'}
    m=MeanVariance(s,c,0.,Constraints(np.zeros(n),np.asarray(upper,float)));result=m.max_sharpe();
    if result.get('status')=='optimal':result['diversification_ratio']=result['sharpe'];result['weights']=np.asarray(result['weights'])
    return result


def describe(cov,w,budgets=None):
    c=np.asarray(cov,float);w=np.asarray(w,float);r=risk_contributions(c,w);vol=r['volatility'];s=np.sqrt(np.diag(c));hhi=float(w@w)
    r|={'diversification_ratio':float(w@s/vol) if vol>1e-12 else None,'effective_positions':1/hhi if hhi>0 else None,'nonzero_count':int((w>1e-6).sum()),'max_weight':float(w.max()),'budget_error':float(np.max(abs(np.asarray(r['shares'])-budgets))) if budgets is not None and r['shares'] is not None else None}
    return r
