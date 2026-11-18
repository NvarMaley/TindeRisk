import json
import re
from collections import Counter

from src.paths import ROOT


def test_fixed_questionnaire_covers_five_dimensions_and_has_stable_choices():
    bank = json.loads((ROOT / "questions" / "fixed_mvp.json").read_text(encoding="utf-8"))
    questions = bank["questions"]
    assert 10 <= len(questions) <= 15
    assert Counter(question["dimension"] for question in questions) == {
        "capacity": 4, "tolerance": 3, "knowledge": 3, "objectives": 1, "constraints": 3,
    }
    ids = [q["id"] for q in questions]
    assert all(re.fullmatch(r"F\d{2}", key) for key in ids)
    assert len(ids) == len(set(ids))

    for question in questions:
        assert question["type"] in {"single", "multiple"}
        options = question["options"]
        option_ids = [option["id"] for option in options]
        assert question["text"].strip() and all(option["text"].strip() for option in options)
        assert len(option_ids) >= 2 and len(set(option_ids)) == len(option_ids)
        assert "unsure" in option_ids
        if question["type"] == "multiple":
            assert set(question["exclusive_option_ids"]) == {"none", "unsure"}
            assert set(question["exclusive_option_ids"]).issubset(option_ids)
