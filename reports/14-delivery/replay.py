"""Independent release checks, run from a V2 checkout with its own Python environment."""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from scipy import sparse

from riskmatch_v2.archive_labels import read_snapshot
from riskmatch_v2.feasibility.engine import Problem
from riskmatch_v2.feasibility.study import market
from riskmatch_v2.interview import CARDS, Interview, route
from riskmatch_v2.matching.engine import Market, engine_replay
from riskmatch_v2.matching.ledger import Ledger, replay_evidence
from riskmatch_v2.matching.mandate import mandate
from riskmatch_v2.universe.model import broad_frontier

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/14-delivery"


def read(file):
    return json.loads((ROOT / file).read_text())


def accepted_ids(names):
    return hashlib.sha256("\n".join(sorted(names)).encode()).hexdigest()


def coverage():
    study = read("reports/univers-complet/resultats.json")
    pack = read("reports/13-application/market.json")
    counts = study["annual"][-1]["classes"]
    classes = np.array(pack["asset_classes"])
    rows = {}
    for cls, n in counts.items():
        mask = classes == cls
        rows[cls] = {
            "screened": n["size"],
            "eligible": n["sum"],
            "blocked": n["size"] - n["sum"],
            "selected_union": int(mask.sum()),
            "options": {
                key: int((np.asarray(w)[mask] > 0).sum())
                for key, w in pack["options"].items()
            },
        }
    assert (
        sum(r["eligible"] for r in rows.values())
        == study["subsets"]["Full universe"]["offered"]
        == pack["universe"]
    )
    assert sum(r["selected_union"] for r in rows.values()) == len(set(pack["symbols"]))
    return rows


def archive_check():
    study = read("reports/univers-complet/resultats.json")
    bundle = ROOT / "data/local/univers" / study["snapshot"]
    filters = [("day", "=", study["date"])]
    members = read_snapshot(bundle / "membership.parquet", filters=filters)
    weights = read_snapshot(bundle / "weights.parquet", filters=filters)
    eligible = members.loc[members.included, "id"]
    with np.load(bundle / "models.npz", allow_pickle=False) as data:
        names = data["names"].tolist()
        assert len(names) == len(set(names)) == len(eligible) and set(names) == set(
            eligible
        )
        p = market(
            names,
            data["mu"][0],
            sparse.load_npz(bundle / "risk_0.npz"),
            read("config/faisabilite-5.json"),
        )
    assert set(weights.id) <= set(names)
    r = broad_frontier(p)
    ref = study["subsets"]["Full universe"]
    assert r["status"] == ref["status"] == "optimal"
    assert abs(r["candidate"]["net"] - ref["net"]) < 1e-6
    return {
        "eligible_identifier_sha256": accepted_ids(eligible),
        "solver_input_identifier_sha256": accepted_ids(p.names),
        "offered": len(p.names),
        "positive_weights_union": int(weights.loc[weights.weight > 0, "id"].nunique()),
        "optimal_net": r["candidate"]["net"],
        "risk": r["candidate"]["risk"],
        "held_above_1e_minus_7": int(
            (np.array(r["candidate"]["weights"]) > 1e-7).sum()
        ),
        "benchmark_net": study["cards"]["60/40 benchmark"]["net"],
        "benchmark_vol": study["cards"]["60/40 benchmark"]["vol"],
    }


def client_replay(label, m):
    case = read(f"reports/07-funding/client-{label}.json")
    iv = Interview(date.fromisoformat(m.day))
    for key in CARDS:
        if key in route(iv.answers):
            iv.record(key, case["answers"].get(key, "skip"))
    iv.confirm()
    iv.save_risk(case["risk_request"], accept=True, bills="yes", comfort="yes")
    policy = mandate(iv, m.day)
    assert (
        not policy["blocked_reason"] and policy["goal_chf"] == case["plan"]["goal_chf"]
    )
    with TemporaryDirectory() as temp:
        ledger = Ledger.create(temp)
        ledger.save_mandate(policy)
        ledger.flow(m.day, policy["capital_chf"], "opening")
        ledger.mark(m.day, m.quotes(m.day))
        account = ledger.account(m.day)
        parts = {"Return": 0.6, "Diversification": 0.4}
        plan = m.plan(parts, policy, account)
        assert plan["valid"]
        draft = ledger.propose(m.day, plan["targets"], parts)
        assert ledger.confirm(draft, m.day) == 1
        later = m.days[1]
        ledger.mark(later, m.quotes(later))
        ledger.flow(later, 1000.0, "deposit")
        now = ledger.account(later)
        revision = m.review(policy, now)["alternative"]
        assert revision and revision["valid"]
        second = ledger.propose(later, revision["targets"], revision["parts"])
        assert ledger.confirm(second, later) == ledger.confirm(second, later) == 2
        rejected = m.plan(parts, policy | {"low": 0.38, "high": 0.42}, account)
        assert not rejected["valid"]
        return {
            "goal_chf": policy["goal_chf"],
            "goal_date": policy["goal_date"],
            "opening_chf": policy["capital_chf"],
            "reserve_chf": policy["reserve_chf"],
            "required_annual_rate": plan["goal_required"],
            "rounded_positions": len(plan["targets"]),
            "volatility": plan["vol"],
            "entry_fee_chf": plan["fee_chf"],
            "final_portfolio_versions": len(ledger.export()["portfolios"]),
            "outside_band": rejected["reason"],
        }


def verify(mode):
    m = Market(public_only=(mode == "public"))
    if mode == "private":
        assert m.source == "Private archived first close", (
            "Private close is required for this run"
        )
    else:
        assert m.source == "Synthetic execution tape"
    result = {
        "tape": m.source,
        "model_id": m.model_id,
        "classes": coverage(),
        "clients": {label: client_replay(label, m) for label in "AB"},
    }
    assert (
        result["clients"]["A"]["required_annual_rate"]
        != result["clients"]["B"]["required_annual_rate"]
    )
    try:
        Problem((), [], sparse.csr_matrix((0, 0)), [], [], [], [], {})
    except ValueError as exc:
        assert "Empty universe" in str(exc)
        result["empty_universe"] = str(exc)
    else:
        raise AssertionError("Accepted an empty investment universe")
    run = engine_replay(public_only=(mode == "public"))
    ref = read("reports/13-application/market-replay.json")[
        "portable" if mode == "public" else "local"
    ]
    for key in ("vol", "net", "fee_chf", "cash_chf"):
        assert abs(run["match"][key] - ref["match"][key]) < 1e-7
    assert (
        abs(run["after_fee_improvement_chf"] - ref["after_fee_improvement_chf"]) < 1e-7
    )
    book = replay_evidence()
    assert all(book["controls"].values())
    result["oil_gain_after_cost_chf"] = run["after_fee_improvement_chf"]
    result["ledger_controls"] = book["controls"]
    if mode == "private":
        result["full_solver"] = archive_check()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["public", "private"])
    args = parser.parse_args()
    result = verify(args.mode)
    print(json.dumps(result, indent=2, allow_nan=False))
