"""Long-only CHF pocket, proportional trading costs and independent bounds."""
from dataclasses import dataclass
from itertools import combinations, product
from heapq import heappop, heappush
from time import monotonic

import cvxpy as cp
import numpy as np
from scipy import sparse
from scipy.optimize import linprog

TOL = 1e-6
GAP = 1e-4  # One basis point of annual expected return.
PAD = 1e-9


@dataclass
class Problem:
    names: tuple
    mu: np.ndarray
    root: object  # Columns are assets. Annual risk is norm(root @ weights).
    lo: np.ndarray
    hi: np.ndarray
    current: np.ndarray
    fees: np.ndarray
    groups: dict  # label -> (look-through coefficients, maximum)
    invested_min: float = 0.
    invested_max: float = 1.
    years: float = 1.
    prefund: bool = False  # Sales unavailable before purchases settle.

    def __post_init__(self):
        n = len(self.names)
        if n == 0 or len(set(self.names)) != n:
            raise ValueError("Empty universe or duplicate identifiers")
        for name in ("mu", "lo", "hi", "current", "fees"):
            x = np.asarray(getattr(self, name), dtype=float)
            if x.shape != (n,) or not np.isfinite(x).all():
                raise ValueError("Invalid Vector: " + name)
            setattr(self, name, x)
        self.root = sparse.csc_matrix(self.root)
        if self.root.shape[1] != n or not np.isfinite(self.root.data).all():
            raise ValueError("Incompatible risk factor")
        if (not 0 <= self.invested_min <= self.invested_max <= 1 or
            not np.isfinite(self.years) or self.years <= 0 or
            np.any(self.lo < 0) or np.any(self.hi > 1) or np.any(self.lo > self.hi) or
            self.current.min() < 0 or self.current.sum() > 1 + PAD or self.fees.min() < 0):
            raise ValueError("Impaired points, horizons, positions or costs")
        for name, (coeff, cap) in self.groups.items():
            coeff = np.asarray(coeff, dtype=float)
            if coeff.shape != (n,) or not np.isfinite(coeff).all() or not np.isfinite(cap):
                raise ValueError("Incomplete limit: " + name)
            self.groups[name] = (coeff, float(cap))

    def evaluate(self, w, low=0., high=None):
        w = np.asarray(w, dtype=float)
        if w.shape != self.mu.shape or not np.isfinite(w).all():
            raise ValueError("Invalid weights")
        delta = w - self.current
        fee = float(self.fees @ abs(delta))
        cash = float(1 - w.sum() - fee)
        risk = float(np.linalg.norm(self.root @ w))
        available = float(1 - self.current.sum())
        sales = float(np.maximum(-delta, 0).sum())
        trade_cash = float(available + (0 if self.prefund else sales) - np.maximum(delta, 0).sum() - fee)
        slack = dict(cash=cash, financement=trade_cash, minimum=float(w.sum()-self.invested_min),
                     maximum=float(self.invested_max-w.sum()), borne_basse=float((w-self.lo).min()),
                     borne_haute=float((self.hi-w).min()), risque_bas=risk-low)
        if high is not None:
            slack["risque_haut"] = high-risk
        slack.update({name: float(cap-a@w) for name,(a,cap) in self.groups.items()})
        error = max(0., -min(slack.values()))
        return dict(weights=w.tolist(), risk=risk, net=float(w@self.mu-fee/self.years),
                    fee=fee, cash=cash, turnover=float(abs(delta).sum()), funding=trade_cash,
                    residual=error, balance_error=abs(w.sum()+cash+fee-1),
                    active=[k for k,v in slack.items() if abs(v)<=TOL], valid=error<=TOL)


class Frontier:
    def __init__(self, p):
        self.p = p
        n = len(p.names)
        unit = sparse.eye(n, format="csr")
        # x = (target weights, absolute trades). t is bounded by 1 for all long-only trades.
        rows = [sparse.hstack([unit, -unit]), sparse.hstack([-unit, -unit])]
        rhs = [*p.current, *-p.current]
        self.g = np.r_[p.mu, -p.fees/p.years]
        self.vols = np.sqrt(np.asarray(p.root.power(2).sum(axis=0)).ravel())
        def row(w, t, limit):
            rows.append(sparse.csr_matrix(np.r_[w,t]))
            rhs.append(limit)
        ones, zeros = np.ones(n), np.zeros(n)
        row(ones, p.fees, 1)
        row(ones, zeros, p.invested_max)
        row(-ones, zeros, -p.invested_min)
        if p.prefund:
            row(ones/2, ones/2+p.fees, 1-p.current.sum()/2)
        for coeff,cap in p.groups.values():
            row(coeff, zeros, cap)
        self.A, self.b = sparse.vstack(rows,format="csr"), np.array(rhs)

    def linear(self, g, lo, hi, tangent=None):
        """Maximise a linear form and construct a feasible dual upper bound on its box."""
        n=len(lo)
        A,b=self.A,self.b
        if tangent is not None:
            a,cap=tangent
            A=sparse.vstack([A,sparse.csr_matrix(np.r_[a,np.zeros(n)])],format="csr")
            b=np.r_[b,cap]
        lower,upper=np.r_[lo,np.zeros(n)],np.r_[hi,np.ones(n)]
        fit=linprog(-g,A_ub=A,b_ub=b,bounds=np.column_stack([lower,upper]),method="highs")
        if not fit.success:
            return None, np.inf, fit.status
        y=np.maximum(-fit.ineqlin.marginals,0.)
        remainder=g-A.T@y
        bound=float(b@y+np.maximum(lower*remainder,upper*remainder).sum()+PAD)
        return fit.x[:n], bound, 0

    def convex(self, lo, hi, high, minimum=False):
        n=len(lo)
        x=cp.Variable(2*n)
        w=x[:n]
        constraints=[self.A@x<=self.b,w>=lo,w<=hi,x[n:]>=0,x[n:]<=1]
        risk=cp.norm(self.p.root@w,2)
        if high is not None:
            constraints.append(risk<=high)
        model=cp.Problem(cp.Minimize(risk) if minimum else cp.Maximize(self.g@x),constraints)
        try:
            model.solve(solver="CLARABEL",tol_gap_abs=1e-9,tol_feas=1e-9)
        except cp.error.SolverError:
            return None
        if model.status!=cp.OPTIMAL or w.value is None:
            return None
        candidate=self.p.evaluate(w.value,high=high)
        return candidate if candidate["valid"] else None

    def tangent(self, w):
        v=self.p.root@w
        norm=np.linalg.norm(v)
        return np.asarray(self.p.root.T@v).ravel()/norm if norm>1e-12 else np.zeros(len(w))

    def vertices(self, lo, hi):
        """Vertices of a small box intersected with the actual linear trading mandate."""
        n=len(lo)
        if n>3:
            return []
        p=self.p
        vertices={}
        for signs in product((-1,1),repeat=n):
            sign=np.array(signs)
            # On each trading orthant t = sign*(w-current).
            mat=(self.A[:,:n]+self.A[:,n:]@sparse.diags(sign)).toarray()
            rhs=self.b+self.A[:,n:]@(sign*p.current)
            mat=np.vstack((mat,np.eye(n),-np.eye(n),-np.diag(sign)))
            rhs=np.r_[rhs,hi,-lo,-sign*p.current]
            useful=np.linalg.norm(mat,axis=1)>1e-12
            mat,rhs=mat[useful],rhs[useful]
            for active in combinations(range(len(rhs)),n):
                a=mat[list(active)]
                if abs(np.linalg.det(a))<1e-12:
                    continue
                w=np.linalg.solve(a,rhs[list(active)])
                if np.max(mat@w-rhs)<=1e-9:
                    vertices[tuple(w.round(10))]=w
        return list(vertices.values())

    def solve(self, *, low=0., high=None, minimum=False, seconds=5., nodes=128):
        if not np.isfinite(low) or low<0 or high is not None and (not np.isfinite(high) or high<low):
            raise ValueError("Invalid risk range")
        if minimum and (low or high is not None):
            raise ValueError("Minimum and incompatible slice")
        start=monotonic()
        p=self.p
        n=len(p.names)
        log=[]
        best=None
        maximum=None
        def result(state, proof, bound=None):
            gap=None if best is None or bound is None else max(0.,bound-best["net"])
            return dict(status=state,proof=proof,candidate=best,upper_net=bound,gap=gap,
                        max_risk_bound=maximum,seconds=monotonic()-start,log=log)
        def accept(w):
            nonlocal best
            c=p.evaluate(w,low,high)
            if c["valid"] and (best is None or c["net"]>best["net"]):
                best=c
        linear,upper,status=self.linear(self.g,p.lo,p.hi)
        if status:
            return result("impossible" if status==2 else "non_concluant","HiGHS linear feasibility check")
        direction=np.r_[self.vols,np.zeros(n)]
        extreme,maximum,_=self.linear(direction,p.lo,p.hi)
        if low>maximum+TOL:
            return result("impossible","triangular limit on volatility")
        if minimum:
            best=self.convex(p.lo,p.hi,None,True)
            if best is None:
                return result("non_concluant","Digital minimum not verified")
            tangent=self.tangent(np.array(best["weights"]))
            _,neg_lower,_=self.linear(np.r_[-tangent,np.zeros(n)],p.lo,p.hi)
            log.append(dict(min_risk_lower=max(0.,-neg_lower)))
            gap=best["risk"]-max(0.,-neg_lower)
            return result("optimal" if gap<=TOL else "candidate","lower limit of risk per hyperplane")
        accept(linear)
        if best and upper-best["net"]<=GAP:
            return result("optimal","global linear bound",upper)
        candidate=self.convex(p.lo,p.hi,high)
        if candidate is None:
            floor=self.convex(p.lo,p.hi,None,True)
            if floor and high is not None:
                _,neg,_=self.linear(np.r_[-self.tangent(np.array(floor["weights"])),np.zeros(n)],p.lo,p.hi)
                if -neg>high+TOL:
                    return result("impossible","minimum risk above the ceiling")
            return result("candidate" if best else "non_concluant","resolution under ceiling unconfirmed",upper)
        base=np.array(candidate["weights"])
        accept(base)
        if high is not None:
            _,cut_bound,_=self.linear(self.g,p.lo,p.hi,(self.tangent(base),high))
            upper=min(upper,cut_bound)
        if best and upper-best["net"]<=GAP:
            return result("optimal","convex relaxation and independent dual bound",upper)
        vertices=self.vertices(p.lo,p.hi) if low>0 else []
        if vertices:
            maximum=min(maximum,max(np.linalg.norm(p.root@v) for v in vertices)+PAD)
            if low>maximum+TOL:
                return result("impossible","maximum at the tops of the polytope")
        def segment(a,b):
            if b is None:
                return
            accept(b)
            if np.linalg.norm(p.root@a)<low<=np.linalg.norm(p.root@b):
                left,right=0.,1.
                for _ in range(45):
                    mid=(left+right)/2
                    if np.linalg.norm(p.root@(a+mid*(b-a)))<low:
                        left=mid
                    else:
                        right=mid
                accept(a+right*(b-a))
        for v in [extreme,linear,*vertices]:
            segment(base,v)
        # Each queued box carries an upper bound even if the search is interrupted.
        queue=[(-upper,0,p.lo,p.hi)]
        serial=0
        finished=-np.inf
        while queue and len(log)<nodes and monotonic()-start<seconds:
            neg,_,lo,hi=heappop(queue)
            bound=-neg
            if best and bound<=best["net"]+GAP:
                finished=max(finished,bound)
                continue
            half=(hi-lo)/2
            if np.linalg.norm(p.root@((hi+lo)/2))+self.vols@half < low-TOL:
                continue
            cw=self.convex(lo,hi,high)
            if cw:
                w=np.array(cw["weights"])
                accept(w)
                segment(base,w)
                cut=(self.tangent(w),high) if high is not None else None
            else:
                cut=None
            witness,new_bound,stat=self.linear(self.g,lo,hi,cut)
            if stat==2:
                continue
            if witness is not None:
                segment(base,witness)
            bound=min(bound,new_bound)
            log.append(dict(node=len(log)+1,upper=bound,best=best["net"] if best else None))
            if best and bound<=best["net"]+GAP or np.max(half)<1e-9:
                finished=max(finished,bound)
                continue
            k=int(np.argmax(half*np.maximum(self.vols,1e-12)))
            mid=(lo[k]+hi[k])/2
            for left in (True,False):
                l,h=lo.copy(),hi.copy()
                if left: h[k]=mid
                else: l[k]=mid
                serial+=1
                heappush(queue,(-bound,serial,l,h))
        upper=max([finished,*[-z[0] for z in queue],best["net"] if best else -np.inf])
        if best and upper-best["net"]<=GAP:
            return result("optimal","global separation and bounds",upper)
        return result("candidate" if best else "non_concluant","research budget or precision",upper if np.isfinite(upper) else None)
