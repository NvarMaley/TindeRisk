import numpy as np
import pytest
from riskmatch.selection.sleeve_ledger import rebalance_paths


def test_transfer_costs_and_constant_budget():
    x=np.array([[.1,-.1],[0,0],[-.05,.05]])
    gross,fees0,_=rebalance_paths(x,[.5,.5],0)
    net,fees,turn=rebalance_paths(x,[.5,.5],10)
    assert gross.sum(axis=1)==pytest.approx(x@np.array([.5,.5]))
    assert fees0.sum()==0
    assert fees[0]==pytest.approx(0,abs=1e-12)
    assert fees[1]>0 and turn[1]>0
    assert net.sum(axis=1)[1]<0
    assert rebalance_paths(x[:,0:1],[1],10)[0].sum(axis=1)==pytest.approx(x[:,0])
