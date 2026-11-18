"""Question bank, likelihoods, and adaptive selection (step 3)."""

import json
from collections.abc import Mapping

from .paths import QUESTIONS


def available_constraint_cards(answers: Mapping[str, str | list[str]]) -> list[dict]:
    """Return unanswered Block D cards whose prerequisites are met, in order."""
    available = []
    for card in load_question_bank():
        if card["bloc"] != "D":
            continue
        condition = card["condition"]
        if card["id"] in answers:
            continue
        if condition is None or answers.get(condition["question_id"]) == condition["equals"]:
            available.append(card)
    return available


def load_question_bank(path=QUESTIONS / "bank.json") -> tuple[dict, ...]:
    """Load the ordered adaptive bank and check the contract used by routing."""
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = []
    seen = {}
    for block, count in (("A", 10), ("B", 20), ("C", 24), ("D", 6)):
        group = data["blocks"][block]
        if group["target_count"] != count or len(group["questions"]) != count:
            raise ValueError(f"Block {block} requires {count} cards")
        for number, card in enumerate(group["questions"], 1):
            key = f"{block}{number:02}"
            valid_types = {"A": {"single"}, "B": {"ordered"}, "C": {"swipe"},
                           "D": {"single", "multiple"}}[block]
            if card["id"] != key or card["bloc"] != block or card["type"] not in valid_types:
                raise ValueError(f"invalid identity or type for {key}")
            if not card["texte"].strip() or not card["options"]:
                raise ValueError(f"{key} requires a prompt and options")
            condition = card["condition"]
            if condition is not None:
                parent = seen.get(condition["question_id"])
                if (parent is None or parent["type"] != "single"
                        or condition["equals"] not in parent["options"]):
                    raise ValueError(f"{key} requires an earlier single-choice prerequisite")
            cards.append(card)
            seen[key] = card
    return tuple(cards)
