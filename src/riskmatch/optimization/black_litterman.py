"""Black–Litterman excess-return posterior; covariance of mean vs predictive risk."""
import numpy as np

VERSION='black-litterman-v3'


def psd(matrix,name):
    a=np.asarray(matrix,float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.isfinite(a).all() or not np.allclose(a,a.T,rtol=1e-8,atol=1e-12):raise ValueError('Invalid '+name)
    eig=np.linalg.eigvalsh(a);scale=max(1.,float(np.max(abs(eig))))
    if eig.min()<-1e-10*scale:raise ValueError(name+' is not PSD')
    return (a+a.T)/2


def equilibrium(cov,weights,delta):
    c=psd(cov,'covariance');w=np.asarray(weights,float)
    if w.shape!=(len(c),) or not np.isfinite(w).all() or np.any(w<0) or not np.isclose(w.sum(),1) or not np.isfinite(delta) or delta<=0:raise ValueError('Invalid equilibrium inputs')
    return delta*(c@w)


def posterior(cov,weights,delta,tau,P=None,q=None,confidence=None,correlation=None):
    c=psd(cov,'covariance');pi=equilibrium(c,weights,delta);n=len(c)
    if not np.isfinite(tau) or not 0<tau<=1:raise ValueError('Tau must lie in (0,1]')
    prior=tau*c
    if P is None or len(P)==0:
        if (q is not None and len(q)) or (confidence is not None and len(confidence)):raise ValueError('View values without view matrix')
        return {'prior_excess':pi,'posterior_excess':pi.copy(),'mean_covariance':prior,'predictive_covariance':c+prior,'omega':np.empty((0,0)),'innovation':np.array([]),'rank':0,'condition':None,'active_views':[],'dropped_views':[],'residual':0.}
    p=np.asarray(P,float);q=np.asarray(q,float);conf=np.asarray(confidence,float);m=len(p)
    if p.shape!=(m,n) or q.shape!=(m,) or conf.shape!=(m,) or not np.isfinite(p).all() or not np.isfinite(q).all() or not np.isfinite(conf).all() or np.any((conf<0)|(conf>1)) or np.any(np.linalg.norm(p,axis=1)<1e-12):raise ValueError('Invalid view dimensions/confidence')
    corr=np.eye(m) if correlation is None else psd(correlation,'view correlation')
    if corr.shape!=(m,m) or not np.allclose(np.diag(corr),1):raise ValueError('Invalid view correlation diagonal')
    keep=[];dropped=[]
    for i in range(m):
        if conf[i]==0:dropped.append({'index':i,'reason':'zero_confidence'});continue
        scale=np.linalg.norm(p[i]);row=p[i]/scale;target=q[i]/scale;duplicate=None
        for j in keep:
            other=p[j]/np.linalg.norm(p[j]);sign=1 if np.allclose(row,other,atol=1e-10) else -1 if np.allclose(row,-other,atol=1e-10) else 0
            if sign:
                if not np.isclose(target,sign*q[j]/np.linalg.norm(p[j]),atol=1e-9):raise ValueError('Conflicting collinear views; reconcile assumptions')
                duplicate=j;break
        if duplicate is None:keep.append(i)
        elif conf[i]>conf[duplicate]:keep[keep.index(duplicate)]=i;dropped.append({'index':duplicate,'reason':'redundant_view'})
        else:dropped.append({'index':i,'reason':'redundant_view'})
    if not keep:
        out=posterior(c,weights,delta,tau);out['dropped_views']=dropped;return out
    p=p[keep];q=q[keep];conf=conf[keep];corr=corr[np.ix_(keep,keep)];cross=prior@p.T;view_prior=p@cross
    d=np.sqrt(np.maximum(np.diag(view_prior),0)*(1-conf)/conf);omega=d[:,None]*corr*d[None,:];system=psd(view_prior+omega,'view system');innovation=q-p@pi
    vals,vec=np.linalg.eigh(system);tol=max(1e-14,float(vals.max())*1e-10);valid=vals>tol;rank=int(valid.sum())
    if np.linalg.norm(vec[:,~valid].T@innovation)>1e-8:raise ValueError('Conflicting exact or singular views')
    inverse=(vec[:,valid]/vals[valid])@vec[:,valid].T if rank else np.zeros_like(system);gain=cross@inverse;mean=pi+gain@innovation;uncertainty=(prior-gain@cross.T);uncertainty=(uncertainty+uncertainty.T)/2
    # Exact Gaussian conditional covariance is PSD; tiny roundoff is tolerated.
    psd(uncertainty,'posterior mean covariance')
    return {'prior_excess':pi,'posterior_excess':mean,'mean_covariance':uncertainty,'predictive_covariance':c+uncertainty,'omega':omega,'innovation':innovation,'rank':rank,'condition':float(vals[valid].max()/vals[valid].min()) if rank else None,'active_views':keep,'dropped_views':dropped,'residual':float(np.linalg.norm(system@(inverse@innovation)-innovation))}


def delta_estimate(returns,rf,weights,fallback=2.5):
    x=np.asarray(returns,float)@np.asarray(weights,float);r=np.asarray(rf,float)
    if len(x)<2 or x.shape!=r.shape or not np.isfinite(x).all() or not np.isfinite(r).all():raise ValueError('Invalid market return history')
    variance=float(np.var(x,ddof=1)*12);excess=float(np.mean(x-r)*12);value=excess/variance if variance>1e-12 else None
    if value is None or not np.isfinite(value) or value<=0:return {'delta':fallback,'raw':value,'source':'declared_fallback_positive_delta','annual_excess':excess,'annual_variance':variance}
    return {'delta':float(value),'raw':float(value),'source':'historical_fixed_anchor_premium_over_variance','annual_excess':excess,'annual_variance':variance}
