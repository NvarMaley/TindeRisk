from collections import Counter

import numpy as np
import pytest

from riskmatch.behavioral.discovery import bank, session, score, canonical_choice, QUOTAS
from riskmatch.behavioral.utility import crra, prospect, explore_likelihoods
from riskmatch.behavioral.pilot_analysis import synthetic_panel, psychometrics, logistic_readiness


def test_bank_structure_and_equivalent_framing():
    items=bank("CHF")
    assert len(items)==60 and len({c["id"] for c in items})==60
    assert Counter(c["block_id"] for c in items)=={k:2*v for k,v in QUOTAS.items()}
    for c in items:
        assert all(c[a][lang] for a in ("canonical_a","canonical_b") for lang in ("en","fr"))
        for alt in (c["canonical_a"],c["canonical_b"]):
            if alt["probabilities"]:assert sum(alt["probabilities"])==pytest.approx(1)
        if c["block_id"]=="trajectory":
            a,b=c["canonical_a"],c["canonical_b"]
            assert a["horizon_days"]==b["horizon_days"]==365 and a["annual_cost"]==b["annual_cost"]
            assert a["path"][1]<b["path"][1]
    frame=[c for c in items if c["block_id"]=="framing"]
    for a,b in zip(frame[::2],frame[1::2]):
        assert a["pair_id"]==b["pair_id"]
        for side in ("canonical_a","canonical_b"):
            assert a[side]["outcomes"]==b[side]["outcomes"] and a[side]["probabilities"]==b[side]["probabilities"]
            assert a[side]["en"]!=b[side]["en"]


@pytest.mark.parametrize("seed",[0,1,42,123,2**32-1])
def test_randomized_balanced_session(seed):
    s=session(seed,"USD");cards=s["cards"]
    assert s==session(seed,"USD")
    assert len(cards)==30 and sum(c["scored"] for c in cards)==20
    assert Counter(c["block_id"] for c in cards)==QUOTAS
    assert {c["presented_order"] for c in cards}==set(range(1,31))
    assert Counter(c["block_id"] for c in cards if c["swapped"])=={k:v//2 for k,v in QUOTAS.items()}
    assert all(c["pair_id"] in {x["id"] for x in cards} for c in cards if c["block_id"]=="consistency")
    positions={c["id"]:c["presented_order"] for c in cards}
    assert all(abs(positions[c["id"]]-positions[c["pair_id"]])>=3 for c in cards if c["block_id"]=="consistency")
    assert s["session_id"]!=session((seed+1)%(2**32),"USD")["session_id"]


def test_scores_extremes_missing_and_non_scored():
    cards=session(42,"CHF")["cards"]
    scored=[c for c in cards if c["scored"]]
    prudent={c["id"]:c["prudent_response"] for c in scored}
    risky={k:"dislike" if v=="like" else "like" for k,v in prudent.items()}
    assert score(42,"CHF",prudent)["score"]==30
    assert score(42,"CHF",risky)["score"]==1
    mixed={**prudent,**dict(list(risky.items())[:10])}
    assert score(42,"CHF",mixed)["score"]==16
    missing=dict(list(prudent.items())[:13]);r=score(42,"CHF",missing)
    assert r["score"] is None and r["coverage"]==.65 and r["sensitivity"][1]==30
    missing[scored[13]["id"]]=scored[13]["prudent_response"]
    assert score(42,"CHF",missing)["score"]==30
    non_scored={c["id"]:"like" for c in cards if not c["scored"]}
    assert score(42,"CHF",{**prudent,**non_scored},confidence=4)["score"]==30
    assert score(42,"CHF",{},confidence=1)["score"] is None
    assert score(42,"CHF",{},confidence=1)["sensitivity"]==[1,30]


def test_consistency_is_canonical_after_swaps_and_framing():
    cards=session(42,"USD")["cards"]
    canonical_b={c["id"]:"like" if c["swapped"] else "dislike" for c in cards}
    assert all(canonical_choice(c,canonical_b[c["id"]])=="B" for c in cards)
    r=score(42,"USD",canonical_b)
    assert r["inconsistencies"]==[] and r["pairs_checked"]==2
    assert r["framing_differences"]==[] and r["framing_pairs_checked"]==3
    repeated=next(c for c in cards if c["block_id"]=="consistency")
    canonical_b[repeated["id"]]="dislike" if canonical_b[repeated["id"]]=="like" else "like"
    assert score(42,"USD",canonical_b)["inconsistencies"]==[repeated["id"]]


@pytest.mark.parametrize("args",[(True,"USD"),(-1,"USD"),(0,"EUR")])
def test_bad_session(args):
    with pytest.raises(ValueError):session(*args)


def test_bad_responses():
    with pytest.raises(ValueError,match="unknown_card"):score(42,"USD",{"unknown":"like"})
    with pytest.raises(ValueError,match="invalid_confidence"):score(42,"USD",{},6)


def test_utility_models_are_separate():
    assert crra([1,2],1).tolist()==pytest.approx([0,np.log(2)])
    assert prospect([-1,1],1,2).tolist()==[-2,1]
    r=explore_likelihoods(42,"USD",{})
    assert r["status"]=="insufficient_choices"
    cards=session(42)["cards"]
    responses={c["id"]:c["prudent_response"] for c in cards if c["scored"]}
    r=explore_likelihoods(42,"USD",responses)
    assert r["n"]==14 and r["status"]=="experimental_weak_identification"
    assert "score" not in r and r["crra"]["nll"]>=0


def test_synthetic_pilot_harness_and_disjoint_splits():
    panel=synthetic_panel(n=120,items=20,seed=42)
    r=psychometrics(panel,bootstrap=30)
    assert len(r["items"])==20 and len(r["test_retest_ci95"])==2
    assert 0<=r["omega_one_factor_approx"]<=1
    m=logistic_readiness(panel)
    tr,va,te=map(set,(m["train_ids"],m["validation_ids"],m["test_ids"]))
    assert len(tr|va|te)==120 and not (tr&va or tr&te or va&te)
    assert len(m["items"])==10 and np.isfinite(m["independent_choice_test_loss"])
