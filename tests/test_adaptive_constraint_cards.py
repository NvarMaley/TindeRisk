import json

import pytest
import yaml

from src.paths import QUESTIONS, ROOT
from src.questionnaire import available_constraint_cards


def test_block_d_cards_route_one_to_one_to_current_investable_sectors():
    cards = json.loads((QUESTIONS / "bank.json").read_text())["blocks"]["D"]["questions"]
    assert [card["id"] for card in cards] == [f"D{index:02}" for index in range(1, 7)]
    sector_card = next(card for card in cards if card["id"] == "D02")
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    exclusive = set(sector_card["params"]["exclusive_option_ids"])
    assert sector_card["type"] == "multiple" and exclusive == {"none", "unsure"}
    assert set(sector_card["options"]) - exclusive == set(config["tickers"]["sectors"])
    assert next(card for card in cards if card["id"] == "D06")["dimension"] == "review_preference"


@pytest.mark.parametrize("answers,expected", [
    ({}, ["D01", "D04", "D05", "D06"]),
    ({"D01": "no"}, ["D04", "D05", "D06"]),
    ({"D01": "unsure"}, ["D04", "D05", "D06"]),
    ({"D01": "yes"}, ["D02", "D03", "D04", "D05", "D06"]),
    ({"D01": "yes", "D02": ["XLE"], "D04": "disallow"}, ["D03", "D05", "D06"]),
    ({"D01": "yes", "D02": ["none"], "D03": "yes", "D04": "disallow",
      "D05": "standard", "D06": "yearly"}, []),
])
def test_eligible_constraint_cards_follow_the_exclusions_gate(answers, expected):
    assert [card["id"] for card in available_constraint_cards(answers)] == expected
