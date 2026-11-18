import json
import math
from collections import Counter

import pytest

from src.paths import QUESTIONS
from src.swipe_cards import build_swipe_cards


def test_swipes_are_reproducible_and_cover_the_log_grid():
    block = json.loads((QUESTIONS / "bank.json").read_text())["blocks"]["C"]
    cards = block["questions"]
    assert cards == build_swipe_cards()
    assert len(cards) == block["target_count"] == 24
    assert [card["id"] for card in cards] == [f"C{n:02}" for n in range(1, 25)]
    thresholds = [card["params"]["phi_seuil"] for card in cards]
    assert (thresholds[0], thresholds[-1]) == (.5, 20)
    for lower, higher in zip(thresholds, thresholds[1:]):
        assert math.log(higher / lower) == pytest.approx(math.log(40) / 23)
    assert Counter(card["params"]["display_order"][0] for card in cards) == {"A": 12, "B": 12}


def test_each_displayed_pair_has_a_real_tradeoff_and_matches_its_model():
    for card in build_swipe_cards():
        a, b = card["options"]["A"], card["options"]["B"]
        phi = card["params"]["phi_seuil"]
        difference = b["sigma"]**2 - a["sigma"]**2
        assert difference > 0
        assert 2 * (b["mu"] - a["mu"]) / difference == pytest.approx(phi, abs=1e-8)
        assert b["outcomes_chf"][0] < a["outcomes_chf"][0] < 0
        assert b["outcomes_chf"][1] > a["outcomes_chf"][1] > 0
        terms = card["params"]
        assert terms["outcome_probabilities"] == [.5, .5] and terms["horizon_years"] == 1
        assert "skip_label" in terms and set(card["options"]) == {"A", "B"}
        for option in (a, b):
            low, high = [amount / terms["starting_chf"] for amount in option["outcomes_chf"]]
            assert (low + high) / 2 == pytest.approx(option["mu"], abs=.000005001)
            assert (high - low) / 2 == pytest.approx(option["sigma"], abs=.000005001)
