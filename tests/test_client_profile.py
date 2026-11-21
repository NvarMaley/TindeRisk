import json
from random import Random

import pytest

from riskmatch import intake, profile
from riskmatch.profile_session import Interview, load_bank
from riskmatch.mandate import required_rate

BANK, TRANSFER = load_bank()
CARDS = {c["id"]: c for c in BANK["cards"]}


def respond(session, key, choice):
    session.apply(dict(action="answer", id=key, choice=choice, seconds=1.25))


def coherent(session, phi=3.0, overrides=None):
    """Yield deterministic, understood financial choices until the profile is frozen."""
    overrides = overrides or {}
    for _ in range(61):
        stage, key = session.current()
        if stage != "profile":
            return
        card = session.cards[key]
        answer = 0
        if key.startswith("C"):
            answer = card["answers"].index(card["correct"])
        if key.startswith("A"):
            answer = int(phi < card["phi_threshold"])
        respond(session, key, overrides.get(key, answer))
    pytest.fail("The interview did not terminate")


def test_bank_and_financial_units():
    assert len(CARDS) == 60
    assert sum(c["core"] for c in CARDS.values()) == 15
    for card in CARDS.values():
        if card["id"].startswith("A"):
            assert profile.choice_threshold(
                card["stake"], card["certain"], card["outcomes"], card["probabilities"]
            ) == pytest.approx(card["phi_threshold"])
    for certain, outcomes in [(80, [90, 110]), (100, [100, 100]), (120, [90, 110])]:
        with pytest.raises(ValueError):
            profile.choice_threshold(100, certain, outcomes, [0.5, 0.5])
    assert profile.choice_threshold(100, 103, [90, 120], [0.5, 0.5]) == pytest.approx(
        16 / 9
    )


def test_comprehension_and_retry():
    s = Interview(intake.sample(), 3)
    respond(s, "C1", -1)
    assert s.current() == ("profile", "C2")
    respond(s, "C2", 2)
    assert s.current() == ("review", None)
    assert s.report()["tolerance"]["bands"] == []
    s.apply(dict(action="revise", id="C1"))
    coherent(s)
    assert s.report()["tolerance"]["bands"] == ["High"]


def test_uncertainty_and_behavior_confirmation():
    missing = {k: 3 for k in profile.CORE if k.startswith("A")}
    assert profile.summary(CARDS, missing)["reason"]
    assert (
        profile.summary(CARDS, {"A01": 1, "A04": 0})["reason"]
        == "Inconsistent trade-offs"
    )
    lo, hi, n = profile.aversion_range(CARDS, {"A02": 2, "A05": -1, "A08": 3})
    assert (lo, hi, n) == pytest.approx((3.6, 4.4, 1))
    pairs = dict(L01=1, L02=0, L03=1, L04=0)
    assert profile.summary(CARDS, pairs)["observation"] is None
    assert profile.summary(CARDS, {**pairs, "B09": 0})["observation"]
    assert profile.summary(CARDS, {"L01": 1, "L02": 0, "B09": 0})["observation"] is None


def test_card_order_balances_sides():
    for k in ("A01", "L04", "V02"):
        assert profile.sides(k, 22) == profile.sides(k, 23)[::-1]
    assert (
        profile.experimental_plan(CARDS, 22)["order"]
        != profile.experimental_plan(CARDS, 23)["order"]
    )


def test_capacity_cannot_raise_or_lower_preference():
    facts = intake.sample()
    fast = dict(
        facts,
        withdraw="48000",
        due="0",
        safety="5000",
        household="Reserve needed from this investment",
        exclusions="Tobacco",
    )
    original, constrained = Interview(facts, 1), Interview(fast, 1)
    for session in (original, constrained):
        coherent(session, 0.1)
    a, b = original.report(), constrained.report()
    for k in ("lo", "hi", "bands", "n"):
        assert a["tolerance"][k] == b["tolerance"][k]
    assert b["capacity"]["free"] == 0 and b["capacity"]["funding_gap"] == 3000
    assert any("exclusion" in x for x in b["capacity"]["reasons"])
    assert a["capacity"]["free"] == 35000
    assert intake.assess(dict(facts, cap=""), {})["free"] == 35000


def test_ranges_and_unsettled_facts():
    raw = dict(
        intake.sample(),
        capital="48000–50000",
        withdraw="12000-15000",
        due="12–24",
        external="1000",
        saving="100",
        household="Reserve needed from this investment",
        safety="1000-2000",
    )
    assess = intake.assess(raw, {"F01": 0})
    assert assess["reserve"] == 14800 and assess["free"] == 33200
    assert not assess["reasons"]
    assert intake.assess(dict(raw, household="Unknown"), {})["free"] is None
    no_withdrawal = dict(raw, withdraw="0", due="", external="", saving="")
    assert intake.assess(no_withdrawal, {})["reserve"] == 2000
    assert intake.assess(dict(raw, currency="EUR"), {})["reasons"]
    assert intake.assess(dict(raw, cap="", horizon=""), {})["required_rate"] is None
    for value in ("50-20", "NaN", "5000 CHF", "-5000"):
        with pytest.raises(ValueError):
            intake.bounds(value, "capital")


def test_goal_return_compounds_monthly_contributions_separately():
    assert required_rate(10000, 0, 2, 12100) == pytest.approx(0.10)
    assert abs(required_rate(1000, 100, 1, 2200)) < 1e-12
    assert required_rate(None, 100, 1, 2200) is None
    assert required_rate(1000, 0, 1, 4000) == pytest.approx(3.0)


def test_frozen_pilot_is_blind_during_validation_and_replayed_on_import():
    s = Interview(intake.sample(), 16, True)
    coherent(s)
    frozen = s.frozen.copy()
    estimate = s.report()["tolerance"]
    assert len(frozen) == 4 and not (set(s.plan["reserve"]) & set(s.answers))
    for x in frozen:
        assert "holdouts" not in json.loads(s.dump())["result"]
        respond(s, x["id"], 1 - x["prediction"] if x["prediction"] is not None else -1)
        assert s.report()["tolerance"] == estimate and s.frozen == frozen
    s.apply(dict(action="confirm"))
    exported = json.loads(s.dump())
    exported["result"]["tolerance"]["lo"] = 999999
    imported = Interview.restore(json.dumps(exported))
    assert imported.report() == s.report() and imported.confirmed
    imported.apply(dict(action="revise", id="B01"))
    assert (
        not imported.confirmed and not imported.frozen and imported.revised_after_freeze
    )
    coherent(imported)
    assert imported.current() == ("review", None)
    assert Interview.restore(imported.dump()).report() == imported.report()


def test_correction_removes_only_invalid_suffix_and_draft_resumes():
    s = Interview(intake.sample(), 7)
    coherent(s, overrides={"B01": 1, "B03": 1})
    assert "B04" in s.answers
    s.apply(dict(action="revise", id="B01"))
    assert "B03" not in s.answers
    coherent(s, overrides={"B01": 2})
    assert "B05" in s.answers and "B04" not in s.answers
    scored = s.report()["tolerance"]
    s.apply(dict(action="facts", facts=dict(s.facts, exclusions="Coal", employer=True)))
    assert s.current() == ("profile", "F05")
    assert "F06" not in s.answers
    assert Interview.restore(s.dump()).answers == s.answers
    coherent(s)
    assert s.report()["tolerance"]["lo"] == scored["lo"]
    assert "F06" in s.answers
    for change in (
        {"versions": [0]},
        {"events": [{"action": "answer", "id": "A18", "choice": 0, "seconds": 0}]},
        {"events": [{"action": "confirm"}]},
        {"initial": {}},
    ):
        with pytest.raises(ValueError):
            Interview.restore(json.dumps({**json.loads(s.dump()), **change}))


def test_all_cards_reachable_and_core_covered_over_seeded_routes():
    reached = set()
    lengths = []
    for seed in range(1000):
        rng = Random(seed)
        m = intake.mandate(intake.sample())
        m.update(
            goal=50000 if seed % 2 else None,
            capital=rng.choice([1000, 10000, 50000]),
            employer=bool(seed % 3),
            variable=bool(seed % 5),
            currency=rng.choice(["CHF", "EUR"]),
            withdraw=rng.choice([0, 5000]),
            household=rng.choice(["Unknown", "Covered elsewhere"]),
            ethics="ESG" if seed % 3 else "",
            strict=seed % 7 == 0,
        )
        plan = profile.experimental_plan(CARDS, seed)
        a = {}
        for _ in range(61):
            k = profile.next_card(CARDS, a, m, plan)
            if k is None:
                break
            assert k not in a and k not in plan["reserve"]
            c = CARDS[k]
            if k.startswith("C") and seed % 4:
                choice = c["answers"].index(c["correct"])
            elif k.startswith("A") and seed % 3:
                choice = int(seed % 18 < c["phi_threshold"])
            elif k.startswith("L") and seed % 5 == 1:
                choice = int(k in ("L01", "L03"))
            else:
                choice = rng.randrange(-1, len(c["answers"]))
            a[k] = choice
        else:
            pytest.fail("Loop in adaptive route")
        reached.update(a)
        if any(k.startswith("S") for k in a):
            assert set(profile.CORE).issubset(a)
            assert sum(k.startswith("S") for k in a) == 1
            assert sum(k.startswith("A") and not CARDS[k]["core"] for k in a) <= 2
            lengths.append(len(a))
        else:
            assert list(a) == ["C1", "C2"]
    assert reached == set(CARDS)
    assert min(lengths) >= 16 and max(lengths) <= 35


def test_early_stop_and_resume_preserve_route_without_premature_classification():
    session = Interview(intake.sample(), 42)
    respond(session, "C1", 1)
    next_id = session.current()[1]
    session.apply(dict(action="stop", id=next_id))
    report = session.report()
    assert report["status"] == "ended_early" and report["tolerance"]["bands"] == []
    restored = Interview.restore(session.dump())
    restored.apply(dict(action="resume"))
    assert restored.current() == ("profile", next_id)
    coherent(restored)
    assert restored.report()["tolerance"]["bands"]


def test_evaluation_keeps_people_separate_and_retains_missing_visits():
    from riskmatch.pilot import evaluate

    def visit(seed, reverse=False):
        s = Interview(intake.sample(), seed, True)
        coherent(s)
        for item in s.frozen:
            predicted = item["prediction"]
            respond(
                s,
                item["id"],
                -1 if predicted is None else int(bool(predicted) ^ reverse),
            )
        return s

    train = visit(42, True)
    first = visit(42)
    other = visit(44)
    sample = [
        dict(id="a", split="baseline", first=train),
        dict(
            id="b",
            split="evaluation",
            first=first,
            retest=first,
            first_date="2026-11-01",
            retest_date="2026-11-08",
        ),
        dict(id="c", split="evaluation", first=other),
        dict(id="d", split="evaluation", first=None),
    ]
    result = evaluate(sample, draws=100)
    assert result["participants"]["invited"] == 3
    assert result["participants"]["eligible"] == 2
    assert result["participants"]["no_first_export"] == 1
    assert result["participants"]["no_retest_export_among_eligible"] == 1
    assert sum(t["count"] for t in result["retest_transitions"]) == 1
    transfer = result["predictions"]["transfer"]
    assert transfer["scores"]["adaptive"]["agreement"] == 1
    assert transfer["paired_accuracy_gain"] == 1
    assert transfer["paired_95pct_interval"] == [1.0, 1.0]
    assert (
        evaluate([])["predictions"]["reserved"]["scores"]["adaptive"]["agreement"]
        is None
    )
    with pytest.raises(ValueError):
        evaluate(sample + [sample[0]])


def test_binary_statements_cover_bank_and_preserve_financial_polarity():
    from riskmatch import swipe

    session = Interview(intake.sample(), 10)
    for key, card in session.items.items():
        for seed in (10, 11):
            order = profile.sides(key, seed)
            item = swipe.prompt(card, order, 0, session.facts)
            assert item["text"].endswith(".") and "?" not in item["context"]
            if key.startswith(("A", "L", "V")):
                assert [item["left"], item["right"]] == order
                assert ("guaranteed balance" in item["text"]) == (item["right"] == 0)
            else:
                step = 0
                while item["left"] is None:
                    step += 1
                    item = swipe.prompt(card, order, step, session.facts)
                assert step < 3
            assert -1 <= item["right"] < len(card["answers"])


def test_swipe_followups_restore_and_never_guess_a_reason():
    session = Interview(intake.sample(), 42)

    def gesture(direction):
        session.apply(
            dict(
                action="swipe",
                id=session.current()[1],
                step=session.step,
                direction=direction,
                seconds=2,
            )
        )

    gesture("right")
    assert session.current()[1] == "A01"
    gesture("pass")
    assert session.step == 1 and "A01" not in session.answers
    assert Interview.restore(session.dump()).statement() == session.statement()
    gesture("left")
    assert session.step == 2
    gesture("pass")
    assert session.answers["A01"] == -1 and session.report()["tolerance"]["n"] == 0
    gesture("right")
    assert session.current()[1] == "B01"
    gesture("left")
    assert "B01" not in session.answers
    session.apply(dict(action="restart_card", id="B01"))
    for _ in range(3):
        gesture("left")
    assert session.answers["B01"] == -1
    gesture("pass")
    gesture("right")
    assert session.answers["A02"] == 2 and session.report()["tolerance"]["n"] == 1
    assert Interview.restore(session.dump()).report() == session.report()

    legacy = Interview(intake.sample(), 42)
    respond(legacy, "C1", 1)
    payload = json.loads(legacy.dump())
    payload.pop("presentation")
    payload["versions"][2] = "1.0-pilot-en"
    resumed = Interview.restore(json.dumps(payload))
    assert resumed.current()[1] == "A01" and resumed.step == 0
