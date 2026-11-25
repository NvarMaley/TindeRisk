"""Monthly constant-budget sleeve allocation, including additional transfer fees."""
import numpy as np
from riskmatch.backtesting.walk_forward import execute


def rebalance_paths(returns, budgets, cost_bps=10.):
    x=np.asarray(returns,float);a=np.asarray(budgets,float)
    if x.ndim!=2 or not len(x) or a.shape!=(x.shape[1],) or not np.isfinite(x).all() or not np.isfinite(a).all() or np.any(x<=-1) or np.any(a<0) or not np.isclose(a.sum(),1) or not 0<=cost_bps<=100:
        raise ValueError("Invalid sleeve ledger")
    a=a/a.sum()
    target=np.r_[a,0.]
    holdings=target.copy()
    rate=cost_bps/10000
    components=[];fees=[];turn=[]
    for row in x:
        opening=float(holdings.sum())
        holdings,delta,fee=execute(holdings,target,rate)
        component=(holdings[:-1]*row-rate*np.abs(delta))/opening
        holdings[:-1]*=1+row
        if not np.isclose(holdings.sum()/opening-1,component.sum(),atol=1e-10):
            raise ArithmeticError("Sleeve ledger not reconciled")
        components.append(component);fees.append(fee/opening);turn.append(float(abs(delta).sum()/opening))
    return np.asarray(components),np.asarray(fees),np.asarray(turn)
