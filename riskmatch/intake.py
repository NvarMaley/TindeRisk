"""Interpret factual inputs conservatively while preserving the original ranges."""

import re
from math import isfinite

from riskmatch.mandate import capacity, required_rate

CURRENCIES = ("CHF", "EUR", "USD", "Other", "Undecided")
HOUSEHOLD = ("Unknown", "Covered elsewhere", "Reserve needed from this investment")
NUMERIC = (
    "capital",
    "goal",
    "contribution",
    "wish",
    "horizon",
    "withdraw",
    "due",
    "external",
    "saving",
    "safety",
    "cap",
)
TEXT = ("project", "exclusions", "preferences", "other_currency")
FLAGS = ("flexible", "variable", "employer")


def blank():
    return dict(
        project="",
        capital="",
        goal="",
        contribution="0",
        wish="",
        horizon="",
        currency="Undecided",
        other_currency="",
        withdraw="",
        due="",
        external="0",
        saving="0",
        flexible=False,
        household="Unknown",
        safety="",
        variable=False,
        employer=False,
        exclusions="",
        preferences="",
        cap="",
    )


def sample():
    return dict(
        blank(),
        project="Home down payment",
        currency="CHF",
        capital="50000",
        horizon="8",
        withdraw="15000",
        due="24",
        household="Covered elsewhere",
        safety="0",
        cap="12",
    )


def bounds(raw, field):
    """Blank is unknown. Hyphens delimit unsigned ranges, with a signed desired return."""
    if not isinstance(raw, str) or len(raw) > 50:
        raise ValueError(f"Invalid input for {field}.")
    if not raw.strip():
        return None
    number = r"(?:\d+(?:\.\d+)?|\.\d+)"
    if field == "wish":
        number = "-?" + number
    m = re.fullmatch(rf"\s*({number})\s*(?:[-–]\s*({number}))?\s*", raw)
    if not m:
        raise ValueError(
            f"Use digits without thousands separators for {field}, e.g. 5000 or 4000–6000."
        )
    low, high = float(m[1]), float(m[2] or m[1])
    if not isfinite(high) or low > high:
        raise ValueError(f"Check the lower and upper values for {field}.")
    if field in ("horizon", "due") and (not low.is_integer() or not high.is_integer()):
        raise ValueError(
            f"Enter whole {'years' if field == 'horizon' else 'months'} for {field}."
        )
    if field == "horizon" and not 1 <= low <= high <= 100:
        raise ValueError("Use 1 to 100 years for the growth horizon, or leave it open.")
    if field == "wish" and low <= -100:
        raise ValueError("A desired annual return must be greater than −100%.")
    return low, high


def validate_intake(raw):
    if not isinstance(raw, dict) or raw.keys() != blank().keys():
        raise ValueError("The factual intake has missing or unknown fields.")
    if any(type(raw[k]) is not bool for k in FLAGS):
        raise ValueError("Invalid factual preference.")
    if any(not isinstance(raw[k], str) or len(raw[k]) > 300 for k in TEXT):
        raise ValueError("Use up to 300 characters per description.")
    if raw["currency"] not in CURRENCIES or raw["household"] not in HOUSEHOLD:
        raise ValueError("Unknown currency or household reserve setting.")
    if (
        raw["currency"] == "Other"
        and raw["other_currency"]
        and not re.fullmatch(r"[A-Za-z]{3}", raw["other_currency"].strip())
    ):
        raise ValueError("Enter a three-letter currency code or leave it open.")
    for field in NUMERIC:
        bounds(raw[field], field)


def mandate(raw):
    validate_intake(raw)
    intervals = {k: bounds(raw[k], k) for k in NUMERIC}
    m = {
        k: None if r is None else r[int(k in ("withdraw", "safety", "goal"))]
        for k, r in intervals.items()
    }
    m.update({k: raw[k] for k in ("project", "currency", "household", *FLAGS)})
    if m["currency"] == "Other" and raw["other_currency"].strip():
        m["currency"] = raw["other_currency"].strip().upper()
    m.update(
        ethics=raw["exclusions"].strip() or raw["preferences"].strip(),
        strict=bool(raw["exclusions"].strip()),
    )
    if m["household"] == "Covered elsewhere":
        m["safety"] = 0.0
    if m["withdraw"] == 0:
        m.update(due=0, external=0.0, saving=0.0)
    return m


def assess(raw, answers):
    m = mandate(raw)
    cap = capacity(m, answers)
    gap = None if cap["reserve"] is None else max(0.0, cap["reserve"] - m["capital"])
    required = (
        required_rate(cap["free"], m["contribution"], m["horizon"], m["goal"])
        if gap == 0
        else None
    )
    currency = {"CHF": "CHF", "EUR": "EUR", "USD": "USD"}.get(raw["currency"])
    if answers.get("F07") == -1:
        cap["reasons"].append("Confirm the spending currency before allocation.")
    if answers.get("F07") in (0, 1, 2, 3):
        declared = CURRENCIES[answers["F07"]]
        if declared != raw["currency"]:
            cap["reasons"].append(
                "The spending currency differs from the intake. Review it before allocation."
            )
    if answers.get("F01") in (0, 1, 2) and cap["reserve"] is not None and m["capital"]:
        # The card asks about initial capital that must remain available. Externally funded
        # withdrawals do not consume that capital. Use both ends when intake is a range.
        upper_fraction = max(0, cap["reserve"] - m["safety"]) / m["capital"]
        maximum_capital = bounds(raw["capital"], "capital")[1]
        if m["withdraw"]:
            withdrawal_min = bounds(raw["withdraw"], "withdraw")[0]
            external_max = bounds(raw["external"], "external")[1]
            savings_max = bounds(raw["saving"], "saving")[1]
            months_max = bounds(raw["due"], "due")[1]
            lower_fraction = (
                max(0, withdrawal_min - external_max - savings_max * months_max)
                / maximum_capital
            )
        else:
            lower_fraction = 0
        band = answers["F01"]
        possible = (
            lower_fraction < 0.25,
            lower_fraction <= 0.5 and upper_fraction >= 0.25,
            upper_fraction > 0.5,
        )
        if not possible[band]:
            cap["reasons"].append(
                "The withdrawal share on the card differs from the reserve implied by your figures."
            )
    if m["employer"]:
        exposure = (
            "Review employer-linked income or holdings before assessing concentration."
        )
    else:
        exposure = None
    return dict(
        **cap,
        funding_gap=gap,
        currency=currency or m["currency"],
        required_rate=required,
        desired_return=bounds(raw["wish"], "wish"),
        risk_cap_pct=m["cap"],
        employer_review=exposure,
        exclusions=raw["exclusions"],
        preferences=raw["preferences"],
        conservative_inputs=m,
    )
