from collections import Counter

import numpy as np
import pytest

from riskmatch.behavioral.discovery import bank, session, score, canonical_choice, QUOTAS
from riskmatch.behavioral.utility import crra, prospect, explore_likelihoods
from riskmatch.behavioral.pilot_analysis import synthetic_panel, psychometrics, logistic_readiness


def test_fixed_bank_and_matched_trajectories():
    items=bank("CHF")
    assert len(items)==len({c["id"] for c in items})==30
    assert Counter(c["block_id"] for c in items)==QUOTAS
    for c in items:
        a,b=c["canonical_a"],c["canonical_b"]
        assert all(alt[lang] for alt in (a,b) for lang in ("en","fr"))
        for alt in (a,b):
            if alt["probabilities"]:
                assert sum(alt["probabilities"])==pytest.approx(1)
        if c["block_id"]=="trajectory":
            assert a["horizon_days"]==b["horizon_days"]==365 and a["annual_cost"]==b["annual_cost"]
            assert a["outcomes"]==b["outcomes"] and a["probabilities"]==b["probabilities"]
            assert min(a["path"][1:3])<min(b["path"][1:3])
        if c["block_id"]=="rare":
            assert a["expected_payoff"]==pytest.approx(b["expected_payoff"])
        if c["block_id"]=="mixed":
            assert a["outcomes"][0]>0>a["outcomes"][1] and b["outcomes"]==[0]
            assert not c["scored"]


@pytest.mark.parametrize("seed",[0,1,42,123,2**32-1])
def test_every_session_has_same_order_and_option_placement(seed):
    s=session(seed,"USD")
    other=session((seed+1)%(2**32),"USD")
    assert s["cards"]==other["cards"]
    assert s["session_id"]!=other["session_id"]
    cards=s["cards"]
    assert sum(c["scored"] for c in cards)==20
    assert sum(c["prudent_response"]=="like" for c in cards)==10
    rare_swaps=[c for c in cards if c["block_id"]=="rare" and c["swapped"]]
    assert {c["dimension"] for c in rare_swaps}=={"rare_gain","rare_loss"}
    assert {c["canonical_a"]["probabilities"][0] for c in rare_swaps}=={.01,.05}
    assert [c["presented_order"] for c in cards]==list(range(1,31))
    assert cards[-1]["pair_id"]==cards[0]["id"]
    assert cards[-1]["swapped"]!=cards[0]["swapped"]


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


def test_consistency_and_comprehension_are_descriptive():
    cards=session(42,"USD")["cards"]
    canonical_b={c["id"]:"like" if c["swapped"] else "dislike" for c in cards}
    assert all(canonical_choice(c,canonical_b[c["id"]])=="B" for c in cards)
    r=score(42,"USD",canonical_b)
    assert r["inconsistencies"]==[] and r["pairs_checked"]==1
    assert r["comprehension_correct"] is False
    assert r["style_profile"]=="000"
    canonical_b["CT02"]="dislike"
    canonical_b["CT01"]="like"
    revised=score(42,"USD",canonical_b)
    assert revised["inconsistencies"]==["CT02"] and revised["comprehension_correct"] is True
    assert revised["score"]==r["score"]==30


@pytest.mark.parametrize(("choices", "status", "lower", "upper", "answered"), [
    ({100:"B", 125:"B", 150:"B", 200:"A"}, "range", 150, 200, 4),
    ({125:"A", 150:"B"}, "inconsistent", 150, 125, 2),
    ({100:"A", 125:"A"}, "atMost", None, 100, 2),
    ({100:"B", 200:"B"}, "above", 200, None, 2),
    ({}, "unanswered", None, None, 0),
])
def test_mixed_gain_thresholds_follow_the_canonical_choice(choices, status, lower, upper, answered):
    cards = session(42)["cards"]
    responses = {card["id"]:card["prudent_response"] for card in cards if card["scored"]}
    for card in cards:
        if card["dimension"] != "mixed_loss_choices":
            continue
        gain, loss = card["canonical_a"]["outcomes"]
        choice = choices.get(gain) if loss == -100 else None
        responses[card["id"]] = "skip" if choice is None else (
            "like" if (choice == "A") != card["swapped"] else "dislike")
    report = score(42, "USD", responses)
    assert report["score"] == 30
    threshold, other = report["mixed_gain_thresholds"]
    assert threshold == {"loss":100, "status":status, "max_refused_gain":lower,
                         "min_accepted_gain":upper, "answered":answered, "total":4}
    assert other["loss"] == 500 and other["status"] == "unanswered"


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
    assert r["n"]==16 and r["status"]=="experimental_weak_identification"
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
