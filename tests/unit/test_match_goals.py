import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from riskmatch.selection.goals import assess, REFERENCE_RUN, VERSION
from riskmatch.selection.goals import holdings_paths


def test_match_goal_assessment_pairs_reference(tmp_path):
    m=json.loads((Path(__file__).resolve().parents[2]/"configs/mandate-example.json").read_text())
    m["constraints"]["allowed_assets"].append("reit")
    m.update(as_of="2026-11-25",horizon_date="2027-11-25",contribution_monthly=0,withdrawal_monthly=0)
    m["goals"][0].update(due_date="2027-11-25",amount=100000)
    archive=tmp_path/"data/processed/walk_forward"
    archive.mkdir(parents=True)
    (archive/f"{REFERENCE_RUN}.json").write_text(json.dumps({"benchmarks":{"cash":{"returns":[0]*80}}}))
    rows={"A":({"SPY":1},{"crash":-.1},np.full(80,.01)),
          "B":({"IEF":1},{"crash":-.05},np.zeros(80))}
    with patch("riskmatch.selection.goals.catalog",return_value=(rows,60,np.zeros(80))),patch(
        "riskmatch.selection.goals.blend",return_value={"budgets":{"A":.6,"B":.4}}):
        result=assess(tmp_path,{"mandate":m,"version":VERSION,"names":["A","B"],"budgets":[.6,.4]})
    assert result["paths"]==1000 and result["horizon_months"]==12
    assert result["matched"]["goals"][0]["probability"]==1
    assert result["reference"]["goals"][0]["probability"]==1
    assert len(result["matched"]["wealth_path"]["dates"])==13


def test_holdings_projection_keeps_joint_returns_and_charges_rebalance():
    history=np.array([[.2,-.2,.01],[-.2,.2,.02]])
    indices=np.array([[0,1],[1,0]])
    assert np.allclose(holdings_paths(history,[.5,.5,0.],indices,cost=0),0.)
    net=holdings_paths(history,[.5,.5,0.],indices)
    assert np.allclose(net[:,0],0.)
    assert np.allclose(net[:,1],-.0002)
    assert np.allclose(holdings_paths(history,[0.,0.,1.],indices),history[indices,-1])
