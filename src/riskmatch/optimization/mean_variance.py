"""Convex funded mean-variance programs; no trades or suitability claims."""
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import linprog, minimize, brentq

VERSION='mean-variance-v1'


@dataclass
class Constraints:
    lower: np.ndarray
    upper: np.ndarray
    gross: float=1.
    # Rows are (name, coefficient vector, lower, upper), all units explicit.
    linear: list=field(default_factory=list)
    previous: np.ndarray|None=None
    turnover: float|None=None  # half L1 change, excluding external flows
    turnover_penalty: float=0. # objective penalty per unit one-way traded weight


def analytic_min_variance(cov):
    c=np.asarray(cov,float);one=np.ones(len(c));z=np.linalg.solve(c,one);return z/z.sum()


class MeanVariance:
    """Monthly/annual units must be consistent; caller supplies decimal returns."""
    def __init__(self,mu,cov,rf,constraints):
        self.mu=np.asarray(mu,float);self.cov=np.asarray(cov,float);self.rf=float(rf);self.n=len(self.mu);self.c=constraints
        n=self.n;c=self.c
        if self.mu.ndim!=1 or n<2 or self.cov.shape!=(n,n) or not np.isfinite(self.mu).all() or not np.isfinite(self.cov).all() or not np.isfinite(rf):raise ValueError('Invalid mean-variance inputs')
        self.cov=(self.cov+self.cov.T)/2;eig=np.linalg.eigvalsh(self.cov)
        if eig[0]<-max(1e-10,abs(eig[-1])*1e-9):raise ValueError('Covariance not PSD')
        self.lipschitz=max(float(eig[-1]),1e-10);self.min_eigenvalue=float(eig[0]);self.cov+=np.eye(n)*max(0.,-eig[0]);self.initial=None
        c.lower=np.asarray(c.lower,float);c.upper=np.asarray(c.upper,float)
        if c.lower.shape!=(n,) or c.upper.shape!=(n,) or not np.isfinite([c.lower,c.upper]).all() or np.any(c.lower>c.upper) or not np.isfinite(c.gross) or c.gross<1 or not np.isfinite(c.turnover_penalty) or c.turnover_penalty<0:raise ValueError('Invalid constraints')
        if c.previous is not None:
            c.previous=np.asarray(c.previous,float)
            if c.previous.shape!=(n,) or not np.isfinite(c.previous).all() or not np.isclose(c.previous.sum(),1):raise ValueError('Invalid reference weights')
        if c.turnover is not None and (c.previous is None or not np.isfinite(c.turnover) or c.turnover<0):raise ValueError('Turnover requires a reference')
        if c.turnover_penalty and c.previous is None:raise ValueError('Turnover penalty requires a reference')
        for name,a,lo,hi in c.linear:
            if np.asarray(a).shape!=(n,) or not np.isfinite(a).all() or not np.isfinite([lo,hi]).all() or lo>hi:raise ValueError('Invalid linear constraint: '+name)
        self.simple=bool(np.all(c.lower>=0) and not c.linear and c.turnover is None)
        self._setup_lp()
        self.feasibility=self.lp(np.zeros(n));self.feasible=self.feasibility.success
        if self.feasible:
            self.initial=self.feasibility.x[:n];self.min_return=float(self.mu@self.lp(self.mu).x[:n]);self.max_return=float(self.mu@self.lp(-self.mu).x[:n])

    def _setup_lp(self):
        n=self.n;c=self.c;self.gross_aux=not np.all(c.lower>=0);self.turn_aux=c.previous is not None and (c.turnover is not None or c.turnover_penalty>0)
        # Avoid auxiliary dimensions for the large simple projected solver unless needed for LP certification.
        self.dim=n*(1+int(self.gross_aux)+int(self.turn_aux));self.bounds=list(zip(c.lower,c.upper));rows=[];rhs=[]
        def row(a):return np.pad(np.asarray(a,float),(0,self.dim-n))
        for name,a,lo,hi in c.linear:rows.extend([row(a),row(-np.asarray(a))]);rhs.extend([hi,-lo])
        if self.gross_aux:
            start=n;self.bounds.extend([(0,c.gross)]*n)
            for i in range(n):
                a=np.zeros(self.dim);a[i]=1;a[start+i]=-1;rows.append(a);rhs.append(0);a=a.copy();a[i]=-1;rows.append(a);rhs.append(0)
            a=np.zeros(self.dim);a[start:start+n]=1;rows.append(a);rhs.append(c.gross)
        if self.turn_aux:
            start=n*(1+int(self.gross_aux));self.bounds.extend([(0,None)]*n)
            for i in range(n):
                a=np.zeros(self.dim);a[i]=1;a[start+i]=-1;rows.append(a);rhs.append(c.previous[i]);a=a.copy();a[i]=-1;rows.append(a);rhs.append(-c.previous[i])
            if c.turnover is not None:
                a=np.zeros(self.dim);a[start:start+n]=1;rows.append(a);rhs.append(c.turnover*2)
        self.A=np.asarray(rows).reshape(-1,self.dim);self.b=np.asarray(rhs);self.eq=row(np.ones(n))[None,:]

    def lp(self,objective,target=None,penalty=0.):
        if self.simple and not penalty:
            # Exact same feasible set; omit redundant L1 auxiliaries when unused.
            return linprog(objective,A_ub=-self.mu[None,:] if target is not None else None,b_ub=[-target] if target is not None else None,A_eq=np.ones((1,self.n)),b_eq=[1],bounds=list(zip(self.c.lower,self.c.upper)),method='highs')
        a=self.A;b=self.b
        if target is not None:a=np.vstack([a,np.pad(-self.mu,(0,self.dim-self.n))]);b=np.r_[b,-target]
        obj=np.pad(objective,(0,self.dim-self.n));
        if self.turn_aux:obj[-self.n:]=penalty/2
        return linprog(obj,A_ub=a if len(a) else None,b_ub=b if len(a) else None,A_eq=self.eq,b_eq=[1],bounds=self.bounds,method='highs')

    def _project(self,v,target=None,threshold=0.):
        c=self.c;mu=self.mu;lo=c.lower;hi=c.upper
        if target is not None:target=min(target,self.max_return-1e-10)
        def solve(beta):
            z=v+beta*mu
            def weights(a):
                q=z-a
                if threshold:q=c.previous+np.sign(q-c.previous)*np.maximum(np.abs(q-c.previous)-threshold,0)
                return np.clip(q,lo,hi)
            low=float(np.min(z-hi)-threshold-1);high=float(np.max(z-lo)+threshold+1)
            root=brentq(lambda a:weights(a).sum()-1,low,high,xtol=1e-12)
            return weights(root)
        x=solve(0.)
        if target is None or mu@x>=target-1e-11:return x
        high=1.
        while mu@solve(high)<target and high<1e9:high*=2
        if high>=1e9 and mu@solve(high)<target-1e-8:raise ValueError('Target projection infeasible')
        root=brentq(lambda b:mu@solve(b)-target,0,high,xtol=1e-10)
        return solve(root)

    def diagnostics(self,w,target=None):
        c=self.c;mu=self.mu;var=float(w@self.cov@w);ret=float(mu@w);vol=float(np.sqrt(max(var,0)));gross=float(np.abs(w).sum());turn=float(np.abs(w-c.previous).sum()/2) if c.previous is not None else None
        residuals={'budget':abs(float(w.sum())-1),'lower':max(0.,float(np.max(c.lower-w))),'upper':max(0.,float(np.max(w-c.upper))),'gross':max(0.,gross-c.gross)};active=[]
        if target is not None:residuals['target_return']=max(0.,target-ret)
        if c.turnover is not None:residuals['turnover']=max(0.,turn-c.turnover)
        for name,a,lo,hi in c.linear:
            value=float(np.asarray(a)@w);residuals[name]=max(0.,lo-value,value-hi)
            if min(abs(value-lo),abs(value-hi))<1e-6:active.append(name)
        if target is not None and abs(ret-target)<1e-6:active.append('target_return')
        if c.turnover is not None and abs(turn-c.turnover)<1e-6:active.append('turnover')
        if abs(gross-c.gross)<1e-6:active.append('gross')
        return {'weights':w.tolist(),'expected_return':ret,'variance':var,'volatility':vol,'sharpe':(ret-self.rf)/vol if vol>1e-10 else None,'gross':gross,'net':float(w.sum()),'turnover':turn,'marginal_risk':(self.cov@w/vol).tolist() if vol>1e-10 else None,'risk_contributions':(w*(self.cov@w)/vol).tolist() if vol>1e-10 else None,'residuals':residuals,'active_constraints':active,'lower_active_count':int(np.sum(abs(w-c.lower)<1e-6)),'upper_active_count':int(np.sum(abs(w-c.upper)<1e-6))}

    def solve(self,*,return_weight=0.,variance_weight=1.,target=None,warm=None,penalty=None):
        if not self.feasible:return {'status':'infeasible','reason':self.feasibility.message}
        if variance_weight<=0 or not np.isfinite([variance_weight,return_weight]).all():raise ValueError('Invalid objective')
        if target is not None and target>self.max_return+1e-9:return {'status':'infeasible','reason':'Target exceeds feasible maximum'}
        c=self.c;penalty=c.turnover_penalty if penalty is None else penalty;mu=self.mu;cov=self.cov;n=self.n
        def value(w):return .5*variance_weight*float(w@cov@w)-return_weight*float(mu@w)+(penalty*np.abs(w-c.previous).sum()/2 if penalty else 0.)
        def grad(w):return variance_weight*(cov@w)-return_weight*mu
        lp=self.lp(np.zeros(n),target)
        if not lp.success:return {'status':'infeasible','reason':lp.message}
        if self.simple:
            step=1/(variance_weight*self.lipschitz);x=self._project(np.asarray(warm) if warm is not None else np.ones(n)/n,target);y=x.copy();t=1.;converged=False
            for i in range(1,2501):
                q=self._project(y-step*grad(y),target,step*penalty/2)
                if value(q)>value(x)+1e-12:y=x.copy();t=1.;q=self._project(y-step*grad(y),target,step*penalty/2)
                if np.max(np.abs(q-x))<2e-9 and i>5:x=q;converged=True;break
                tn=(1+np.sqrt(1+4*t*t))/2;y=q+(t-1)/tn*(q-x);x=q;t=tn
            solver='projected_fista';message='Projected iterate tolerance' if converged else 'Iteration limit'
        else:
            a=self.A;b=self.b
            if target is not None:a=np.vstack([a,np.pad(-mu,(0,self.dim-n))]);b=np.r_[b,-target]
            def fun(z):return .5*variance_weight*float(z[:n]@cov@z[:n])-return_weight*float(mu@z[:n])+(penalty*np.sum(z[-n:])/2 if self.turn_aux else 0.)
            def jac(z):
                g=np.pad(grad(z[:n]),(0,self.dim-n));
                if self.turn_aux:g[-n:]=penalty/2
                return g
            cons=[{'type':'eq','fun':lambda z:self.eq@z-1,'jac':lambda z:self.eq}]
            if len(a):cons.append({'type':'ineq','fun':lambda z:b-a@z,'jac':lambda z:-a})
            z0=lp.x
            if warm is not None and self.dim==n and max(self.diagnostics(np.asarray(warm),target)['residuals'].values())<1e-7:z0=np.asarray(warm)
            opt=minimize(fun,z0,jac=jac,bounds=self.bounds,constraints=cons,method='SLSQP',options={'ftol':1e-12,'maxiter':500});x=opt.x[:n];i=int(opt.nit);converged=opt.success;solver='SLSQP';message=str(opt.message)
        d=self.diagnostics(x,target);g=grad(x);oracle=self.lp(g,target,penalty);gap=None
        if oracle.success:
            z=oracle.x[:n];gap=max(0.,float(g@(x-z)+(penalty*(np.abs(x-c.previous).sum()-np.abs(z-c.previous).sum())/2 if penalty else 0.)))
        tolerance=2e-6*max(1.,variance_weight,return_weight,penalty);valid=max(d['residuals'].values())<2e-7 and gap is not None and gap<=tolerance
        return d|{'status':'optimal' if valid else 'unconverged','solver':solver,'message':message,'iterations':i,'objective':value(x),'optimality_gap':gap,'optimality_gap_tolerance':tolerance,'constraint_tolerance':2e-7,'warm_start':warm is not None and self.simple,'target':target}

    def frontier(self,points=9):
        minimum=self.solve(penalty=0.)
        if minimum['status']!='optimal':return minimum,[]
        lo=minimum['expected_return'];hi=self.max_return;rows=[minimum]
        for target in np.linspace(lo,hi,points)[1:]:
            # Exact extreme can be degenerate; LP certifies existence.
            rows.append(self.solve(target=float(target),warm=rows[-1].get('weights'),penalty=0.))
        return minimum,rows

    def max_sharpe(self,frontier=None):
        if not self.feasible:return {'status':'infeasible','reason':self.feasibility.message}
        if self.max_return<=self.rf+1e-10:return {'status':'unavailable','reason':'No positive feasible excess return; no positive tangency solution'}
        minimum,rows=(self.solve(penalty=0.),[]) if frontier is None else frontier
        maximum=self.lp(-self.mu);max_w=maximum.x[:self.n];max_d=self.diagnostics(max_w)
        if max_d['volatility']<1e-10:return {'status':'unbounded','reason':'Positive excess with zero modeled risk'}
        candidates=[r for r in [minimum,*rows] if r.get('status')=='optimal' and r['expected_return']>self.rf]
        if any(r['volatility']<1e-10 for r in candidates):return {'status':'unbounded','reason':'Positive excess with zero modeled risk'}
        best=max([max_d,*candidates],key=lambda r:r['sharpe']);k=best['variance']/(best['expected_return']-self.rf);warm=best['weights'];last=None
        # Tangency via convex QPs: min 1/2 variance - k*mean, k=variance/excess.
        # At the fixed point convex optimality + Cauchy-Schwarz certify the positive ratio.
        low=0.;high=None
        for i in range(30):
            r=self.solve(return_weight=k,warm=warm,penalty=0.)
            if r.get('status')!='optimal':return {'status':'unconverged','reason':'Tangency QP not certified','last_qp':r.get('message')}
            excess=r['expected_return']-self.rf;var=r['variance'];residual=k*excess-var;last=r;warm=r['weights']
            if excess>0 and var<1e-20:return {'status':'unbounded','reason':'Positive excess with zero modeled risk'}
            if excess>0 and abs(residual)<=max(1e-9,1e-6*var):return r|{'method':'positive_excess_convex_qp_tangency','tangency_residual':abs(residual),'tangency_iterations':i+1}
            if residual<0:low=k
            else:high=k
            proposal=var/excess if excess>0 else max(2*k,1e-6)
            if high is not None and not low<proposal<high:proposal=(low+high)/2
            elif proposal<=low:proposal=max(2*k,low+1e-6)
            k=proposal
        # A bracketed root is more robust for nearly flat tangency maps.
        # Reuse feasible QP solutions and certify the actual final fixed-point residual.
        best=None
        def residual_at(k):
            nonlocal warm,best
            q=self.solve(return_weight=float(k),warm=warm,penalty=0.)
            if q.get('status')!='optimal':raise ValueError('Uncertified tangency QP')
            warm=q['weights'];e=q['expected_return']-self.rf;v=q['variance'];res=float(k*e-v)
            if e>0 and (best is None or abs(res)<best[0]):best=(abs(res),q)
            return res
        try:
            a=0.;b=max(k,1e-6);fa=residual_at(a);fb=residual_at(b)
            for _ in range(30):
                if fb>=0:break
                b*=2;fb=residual_at(b)
            if fa<0 and fb>=0:
                root=brentq(residual_at,a,b,xtol=1e-11,maxiter=64);residual_at(root)
                if best is not None and best[0]<=max(1e-8,1e-5*best[1]['variance']):
                    return best[1]|{'method':'positive_excess_bracketed_convex_qp_tangency','tangency_residual':best[0],'tangency_iterations':30,'tangency_tolerance':max(1e-8,1e-5*best[1]['variance'])}
        except ValueError:pass
        return {'status':'unconverged','reason':'Tangency fixed point not certified','last_residual':float(abs(residual))}
