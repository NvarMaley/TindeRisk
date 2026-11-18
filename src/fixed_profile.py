"""Explainable scoring rules for the fixed questionnaire at Step 3.0c."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from math import isclose

from .paths import ROOT
from .profiling import RISK_BANDS, RiskBand, category_from_profile, tolerance_volatility


# Question IDs and option IDs come from questions/fixed_mvp.json.
CAPACITY_RULES = {
    "F01": {"lt_2y": .05, "2_to_lt_5y": .08, "5_to_lt_10y": .12, "ge_10y": .15, "unsure": .04},
    "F02": {"none": .15, "gt_0_to_lt_25pct": .10, "25_to_lt_50pct": .06, "ge_50pct": .04, "unsure": .04},
    "F03": {"lt_1m": .04, "1_to_lt_3m": .06, "3_to_lt_6m": .10, "ge_6m": .15, "unsure": .04},
    "F04": {"lt_5pct": .03, "5_to_lt_10pct": .05, "10_to_lt_20pct": .09,
            "ge_20pct": .12, "no_payment": .15, "unsure": .04},
}
TOLERANCE_POINTS = {
    "F05": {"reduce_risk": 0., "keep_allocation": .5, "increase_risk": 1., "unsure": 0.},
    "F06": {"lt_5pct": 0., "5_to_lt_10pct": 1 / 3, "10_to_lt_20pct": 2 / 3,
            "ge_20pct": 1., "unsure": 0.},
    "F07": {"smaller_swings": 0., "middle": .5, "larger_swings": 1., "unsure": 0.},
}


@dataclass(frozen=True)
class FixedScoringResult:
    """Internal scoring output. The shared profile format follows in Step 3.0d."""

    tolerance_points: dict[str, float]
    tolerance_score: float
    risk_aversion: float
    tolerance_volatility: float
    capacity_caps: dict[str, float]
    capacity_volatility: float
    binding_capacity_items: tuple[str, ...]
    effective_volatility: float
    band: RiskBand | None
    # Only the risk gate is evaluated here. Portfolio constraints still apply.
    reference_within_limit: bool
    clarification_items: tuple[str, ...]


def score_fixed_profile(answers: Mapping[str, str | list[str]], *,
                        reference_sharpe: float) -> FixedScoringResult:
    """Validate a complete F01–F14 submission and apply the fixed score."""
    bank = json.loads((ROOT / "questions/fixed_mvp.json").read_text(encoding="utf-8"))
    expected = {question["id"] for question in bank["questions"]}
    if set(answers) != expected:
        missing = sorted(expected - answers.keys())
        unexpected = sorted(answers.keys() - expected)
        raise ValueError(f"answer IDs differ from questionnaire; missing={missing}, unexpected={unexpected}")

    for question in bank["questions"]:
        key = question["id"]
        answer = answers[key]
        options = {option["id"] for option in question["options"]}
        if question["type"] == "single":
            if not isinstance(answer, str) or answer not in options:
                raise ValueError(f"{key} requires one valid answer")
            continue
        if (not isinstance(answer, list) or not answer
                or any(not isinstance(choice, str) or choice not in options for choice in answer)
                or len(answer) != len(set(answer))):
            raise ValueError(f"{key} requires distinct valid choices")
        if len(answer) > 1 and set(answer).intersection(question["exclusive_option_ids"]):
            raise ValueError(f"{key} requires exclusive choices to stand alone")

    points = {key: rule[answers[key]] for key, rule in TOLERANCE_POINTS.items()}
    caps = {key: rule[answers[key]] for key, rule in CAPACITY_RULES.items()}
    score = sum(points.values()) / len(points)
    aversion = 7 - 4.5 * score
    tolerance = tolerance_volatility(aversion, reference_sharpe)
    capacity = min(caps.values())
    effective, band = category_from_profile(tolerance, capacity)
    if effective < RISK_BANDS[0].min_volatility:
        band = None

    uncertain = tuple(key for key in (*CAPACITY_RULES, *TOLERANCE_POINTS, "F12", "F13", "F14")
                      if answers[key] in ("unsure", ["unsure"]))
    reference_within_limit = (
        not uncertain and band is not None
        and (band.reference_volatility <= effective
             or isclose(band.reference_volatility, effective, rel_tol=0, abs_tol=1e-12))
    )
    return FixedScoringResult(points, score, aversion, tolerance, caps, capacity,
                              tuple(key for key, cap in caps.items() if cap == capacity),
                              effective, band, reference_within_limit, uncertain)
