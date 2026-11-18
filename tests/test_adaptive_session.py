from collections import Counter

import numpy as np
import pytest

from src.adaptive_session import MIRROR_ID, AdaptiveSession, VarianceSelector
from src.adaptive_profile import AversionPosterior
from src.questionnaire import load_question_bank


def test_selector_matches_explicit_expected_posterior_variance():
    posterior = AversionPosterior.prior()
    selector = VarianceSelector(posterior.theta, load_question_bank())
    def expected_variance(key):
        rows = selector.models[key][1]
        return sum(float(row @ posterior.mass) * posterior.update(row).summary()["theta_sd"]**2
                   for row in rows if row @ posterior.mass > 0)
    expected = min((key for key in selector.ids if key.startswith("C") and key != "C01"),
                   key=expected_variance)
    assert selector.choose(posterior, {"C01": "A"}, ("C",))["id"] == expected


@pytest.mark.parametrize("exclude", ["yes", "no"])
def test_session_budget_required_cards_and_mirror(exclude):
    session = AdaptiveSession()
    while (card := session.next_card()) is not None:
        key = card["id"]
        if key == MIRROR_ID:
            original = session.selector.cards[session.original_swipe]
            assert card["params"]["display_order"] == original["params"]["display_order"][::-1]
            session.answer(key, "B")
        else:
            choice = {"D01": exclude, "D02": ["none"]}.get(key, next(iter(card["options"])))
            session.answer(key, choice)
    assert len(session.answers) == 15
    assert {"A01", "A02", "A03", "A04", "D01", "D04", "D05", "D06", MIRROR_ID} <= session.answers.keys()
    assert ("D02" in session.answers) == (exclude == "yes")
    counts = Counter(session.selector.cards[key]["bloc"] for key in session.answers if key in session.selector.cards)
    assert counts["B"] >= 2 and counts["C"] >= 2 and session.inconsistent
    assert session.message and np.isclose(session.posterior.mass.sum(), 1)


def test_all_passed_tolerance_cards_stop_without_inventing_mirror():
    session = AdaptiveSession()
    while (card := session.next_card()) is not None:
        key = card["id"]
        session.answer(key, "no" if key == "D01" else
                       "unsure" if card["bloc"] in ("B", "C") else next(iter(card["options"])))
    assert len(session.answers) == 15
    assert MIRROR_ID not in session.answers
    np.testing.assert_allclose(session.posterior.mass, AversionPosterior.prior().mass)
