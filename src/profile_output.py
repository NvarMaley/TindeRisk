"""Build the versioned JSON-compatible fixed-profile output."""

import json
from collections.abc import Mapping

from .fixed_profile import score_fixed_profile
from .paths import QUESTIONS

PROFILE_SCHEMA_VERSION = 1
SCORING_VERSION = "1.0"
QUESTIONNAIRE_VERSION = "0.1"


def build_profile(answers: Mapping[str, str | list[str]], *,
                  reference_sharpe: float) -> dict:
    """Build the v1 profile using the fixed scorer and questionnaire choices."""
    questionnaire = json.loads((QUESTIONS / "fixed_mvp.json").read_text(encoding="utf-8"))
    if questionnaire["version"] != QUESTIONNAIRE_VERSION:
        raise ValueError("unsupported questionnaire version for the v1 profile")
    result = score_fixed_profile(answers, reference_sharpe=reference_sharpe)
    exclusions = answers["F12"]
    band = result.band
    category = None if band is None else {
        "id": band.key,
        "range": [band.min_volatility, band.max_volatility],
        "reference_volatility": band.reference_volatility,
    }
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "questionnaire_version": questionnaire["version"],
        "scoring_version": SCORING_VERSION,
        "answers": {key: list(value) if isinstance(value, list) else value
                    for key, value in answers.items()},
        "risk": {
            "reference_sharpe": reference_sharpe,
            "tolerance_score": result.tolerance_score,
            "risk_aversion": result.risk_aversion,
            "tolerance_volatility": result.tolerance_volatility,
            "capacity_volatility": result.capacity_volatility,
            "capacity_caps": result.capacity_caps,
            "binding_capacity_items": list(result.binding_capacity_items),
            "effective_volatility": result.effective_volatility,
            "category": category,
            "clarification_items": list(result.clarification_items),
            "reference_check_passed": result.reference_within_limit,
        },
        "constraints": {
            "excluded_groups": None if exclusions == ["unsure"] else
                               [item for item in exclusions if item != "none"],
            "allow_borrowing": {"allow": True, "disallow": False, "unsure": None}[answers["F13"]],
            "max_etf_weight": {"standard": .35, "cap_25pct": .25, "cap_20pct": .20,
                               "unsure": None}[answers["F14"]],
        },
    }
