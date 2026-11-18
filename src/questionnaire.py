"""Question bank, likelihoods, and adaptive selection (step 3)."""

import json
from collections.abc import Mapping

from .paths import QUESTIONS


def available_constraint_cards(answers: Mapping[str, str | list[str]]) -> list[dict]:
    """Return unanswered Block D cards whose prerequisites are met, in order."""
    bank = json.loads((QUESTIONS / "bank.json").read_text(encoding="utf-8"))
    available = []
    for card in bank["blocks"]["D"]["questions"]:
        condition = card["condition"]
        if card["id"] in answers:
            continue
        if condition is None or answers.get(condition["question_id"]) == condition["equals"]:
            available.append(card)
    return available
