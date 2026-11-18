import json
from collections import Counter

from src.paths import QUESTIONS


def test_capacity_bank_preserves_four_fixed_choice_vocabularies():
    bank = json.loads((QUESTIONS / "bank.json").read_text())
    fixed = json.loads((QUESTIONS / "fixed_mvp.json").read_text())
    block = bank["blocks"]["A"]
    cards = block["questions"]
    assert len(cards) == block["target_count"] == 10
    assert [card["id"] for card in cards] == [f"A{number:02}" for number in range(1, 11)]
    assert Counter(card["dimension"] for card in cards) == {
        "capacity": 8, "objectives": 1, "knowledge": 1,
    }
    fixed_vocabulary = {q["id"]: {option["id"] for option in q["options"]}
                        for q in fixed["questions"]}
    anchors = [card for card in cards if "fixed_question" in card["params"]]
    assert [card["params"]["fixed_question"] for card in anchors] == ["F01", "F02", "F03", "F04"]
    for card in cards:
        assert card["bloc"] == "A" and card["type"] == "single" and card["condition"] is None
        assert 3 <= len(card["options"]) <= 6
        assert "unsure" in card["options"]
    for card in anchors:
        assert card["dimension"] == "capacity"
        assert set(card["options"]) == fixed_vocabulary[card["params"]["fixed_question"]]
