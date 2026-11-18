import json
from collections import Counter

from src.paths import QUESTIONS


def test_tolerance_cards_define_an_ordered_scale_without_ranking_skips():
    cards = json.loads((QUESTIONS / "bank.json").read_text())["blocks"]["B"]["questions"]
    assert [card["id"] for card in cards] == [f"B{index:02}" for index in range(1, 21)]
    assert len({card["texte"] for card in cards}) == len(cards)
    assert Counter(card["params"]["theme"] for card in cards) == {
        "reaction": 5, "loss_comfort": 5, "risk_mix": 5, "tradeoff": 5,
    }
    for card in cards:
        assert card["bloc"] == "B" and card["type"] == "ordered"
        assert card["dimension"] == "tolerance"
        assert card["params"]["ordered_option_ids"] == ["low", "medium_low", "medium_high", "high"]
        assert set(card["options"]) == set(card["params"]["ordered_option_ids"]) | {"unsure"}
        assert len(set(card["options"].values())) == 5
