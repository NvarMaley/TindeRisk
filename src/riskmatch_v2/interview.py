"""Questionnaire V2. Derivations use only active, dated responses."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from importlib.resources import files
import json
from math import isfinite
from typing import Any, TypedDict


BANK = json.loads(files("riskmatch_v2").joinpath("questionnaire/banque.json").read_text())
CARDS = {card["id"]: card for card in BANK["cards"]}
SKIP = "skip"


class Interval(TypedDict):
    low: float
    high: float


class Flow(Interval):
    date: str | None
    currency: str
    direction: str
    certainty: str


class Rule(TypedDict):
    scope: str
    strength: str
    priority: str
    missing: str


@dataclass(frozen=True)
class Answer:
    card: str
    value: Any
    at: str


@dataclass(frozen=True)
class Facts:
    capital_chf: Interval | None
    horizon: str | None
    flows: list[Flow] | None
    capacity_loss_chf: Interval | None


@dataclass(frozen=True)
class Goal:
    amount: dict | None
    desired_annual_pct: Interval | None
    risk_request: dict | None
    risk_bounds_pct: dict | None


# Earlier exports used French values for closed-choice fields.
LEGACY_CHOICES = {'apport': 'contribution',
 'autre': 'other',
 'cible_tranche': 'target_band',
 'confirmé': 'confirmed',
 'demander une clarification': 'ask for clarification',
 'devise': 'currency',
 'employeur': 'employer',
 'faible': 'low',
 'foyer': 'household',
 'haute': 'high',
 'impérative': 'mandatory',
 'incertain': 'uncertain',
 'moyenne': 'medium',
 'pays': 'country',
 'plafond': 'cap',
 'poche': 'investment sleeve',
 'retrait': 'withdrawal',
 'secteur': 'sector',
 'signaler et comparer': 'flag and compare',
 'souple': 'soft',
 'suspendre': 'suspend',
 'émetteur': 'issuer'}


def validated(card, value):
    if value == SKIP:
        return value
    if card["kind"] == "binary":
        if value not in ("yes", "no"):
            raise ValueError("Unknown choice")
        return value
    repeat = card["kind"] == "rows"
    if repeat and not isinstance(value, list):
        raise ValueError("List of lines expected")
    rows = value if repeat else [value]
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {f["id"] for f in card["fields"]}:
            raise ValueError("Inform each field or pass the card.")
        cleaned = {}
        for spec in card["fields"]:
            key, kind = spec["id"], spec["type"]
            val = row[key]
            if kind in ("number", "signed"):
                if isinstance(val, bool) or val in ("", None):
                    raise ValueError("Missing amount or percentage")
                val = float(val)
                if not isfinite(val) or (kind == "number" and val < 0):
                    raise ValueError("Invalid numerical value")
            elif kind in ("date", "optional_date"):
                if kind == "optional_date" and not val:
                    val = None
                else:
                    val = date.fromisoformat(val).isoformat()
            elif kind == "select":
                if isinstance(val, str):
                    val = LEGACY_CHOICES.get(val, val)
                if val not in spec["options"]:
                    raise ValueError("Invalid field selection")
            elif kind == "text":
                if not isinstance(val, str) or not val.strip():
                    raise ValueError("Specify the perimeter or pass the card.")
                val = val.strip()
            cleaned[key] = val
        if "low" in cleaned and cleaned["low"] > cleaned["high"]:
            raise ValueError("The maximum shall be greater than or equal to the minimum.")
        result.append(cleaned)
    return result if repeat else result[0]


def understood(values):
    return values.get("C01") == "yes" or values.get("C02") == "yes"


def gamble_bounds(values, *, cards=CARDS):
    bounds = {}
    if understood(values) and values.get("G00") == "yes":
        for key, card in cards.items():
            if "gamble" not in card or values.get(key) not in ("yes", "no"):
                continue
            g = card["gamble"]
            lo, hi, certain = [g[k] / g["stake"] - 1 for k in ("low", "high", "certain")]
            cutoff = 2 * ((lo + hi) / 2 - certain) / ((hi - lo) / 2) ** 2
            bounds[key] = ("low" if values[key] == "yes" else "high", cutoff)
    return bounds


def intersection(bounds):
    low = max((v for side, v in bounds.values() if side == "low"), default=None)
    high = min((v for side, v in bounds.values() if side == "high"), default=None)
    state = "insufficient" if not bounds else "one-sided"
    if low is not None and high is not None:
        state = "contradiction" if low > high else "bounded"
    return dict(low=low, high=high, state=state)


def matches(term, values):
    if term == "@understood":
        return understood(values)
    if term == "@conflict":
        return intersection(gamble_bounds(values))["state"] == "contradiction"
    if term == "@discord":
        choices = [values.get(k) for k in ("G01", "G02", "G03")]
        return (values.get("T01") == "yes" and choices.count("yes") >= 2
                or values.get("T01") == "no" and choices.count("no") >= 2)
    if term == "@inversion":
        return all({values.get(a), values.get(b)} == {"yes", "no"}
                   for a, b in (("L01", "L02"), ("L03", "L04")))
    path, expected = term.split("=")
    key, _, child = path.partition(".")
    val = values.get(key)
    if child:
        val = val.get(child) if isinstance(val, dict) else None
    return val == expected


def route(answers):
    active, values = [], {}
    for key, card in CARDS.items():
        if card["when"] and not any(all(matches(t, values) for t in clause) for clause in card["when"]):
            continue
        active.append(key)
        if key in answers:
            values[key] = answers[key]
    return active


def cash_events(facts, as_of):
    """Group protected CHF flows by day, withdrawals before deposits."""
    issues = []
    horizon = date.fromisoformat(facts.horizon) if facts.horizon else None
    if horizon is None or horizon < as_of:
        issues.append("F02 · missing or past horizon")
    if facts.flows is None:
        issues.append("F03 · unknown flow")
    events = defaultdict(lambda: [0., 0., 0., 0.])
    for flow in facts.flows or []:
        if flow["direction"] == "contribution" and flow["certainty"] != "confirmed":
            continue
        when = date.fromisoformat(flow["date"]) if flow["date"] else None
        if horizon and when and when > horizon:
            continue
        if not when or when < as_of or flow["currency"] != "CHF":
            issues.append("F03 · date to be specified, flow passed to check or conversion to CHF required")
            continue
        day = events[when]
        if flow["direction"] == "withdrawal":
            day[0] += flow["low"] if flow["certainty"] == "confirmed" else 0
            day[1] += flow["high"]
        else:
            day[2] += flow["high"]
            day[3] += flow["low"]
    return events, issues


def liquidity(facts, as_of):
    events, issues = cash_events(facts, as_of)
    low = high = running_low = running_high = 0.
    for out_low, out_high, in_high, in_low in (events[d] for d in sorted(events)):
        running_low += out_low
        running_high += out_high
        low, high = max(low, running_low), max(high, running_high)
        running_low -= in_high
        running_high -= in_low
    reserve = None if issues else dict(low=low, high=high)
    pocket = deficit = None
    cap = facts.capital_chf
    if cap is None:
        issues.append("F01 · unknown capital")
    elif reserve is not None:
        pocket = dict(low=max(0, cap["low"] - high), high=max(0, cap["high"] - low))
        deficit = dict(low=max(0, low - cap["high"]), high=max(0, high - cap["low"]))
    return dict(reserve_chf=reserve, investable_chf=pocket, shortfall_chf=deficit, issues=issues)


def derive(answers, as_of):
    active = route(answers)
    values = {key: answers[key] for key in active if key in answers}
    def known(key):
        val = values.get(key)
        return None if val == SKIP else val
    facts = Facts(known("F01"), (known("F02") or {}).get("date"), known("F03"), known("F04"))
    goal = Goal(known("F05"), known("P01"), known("P02"), known("P03") or known("P04"))
    bounds = gamble_bounds(values)
    phi = intersection(bounds)
    phi["evidence"] = bounds
    phi["without"] = {k: intersection({i: v for i, v in bounds.items() if i != k}) for k in bounds}
    rules: dict[str, list[Rule] | None] = {k: known(k) for k in ("P06","P07","P08","P09","P10")}
    blockers = [dict(card=k, scope=r["scope"]) for k, rows in rules.items() for r in rows or []
                if r["strength"] == "mandatory"]
    motives = {"D02": "liquidity to be checked in F03", "D03": "desired stability",
               "D04": "market anticipation"}
    signals = {k: known(k) for k in active if CARDS[k]["kind"] == "binary" and "gamble" not in CARDS[k]}
    budget = liquidity(facts, as_of)
    clarifications = list(budget["issues"])
    if phi["state"] == "contradiction":
        clarifications.append("G04 · review arbitrations or maintain conflict")
    if known("D02") == "yes" and not any(f["direction"] == "withdrawal" for f in facts.flows or []):
        clarifications.append("D02/F03 · specify the expenditure mentioned")
    if goal.amount and (not goal.amount["date"] or date.fromisoformat(goal.amount["date"]) <= as_of):
        clarifications.append("F05 · future date of target to be specified")
    if matches("@inversion", values):
        clarifications.append("L05 · confirm sensitivity to formulation")
    return dict(clarifications=clarifications, facts=asdict(facts), goal=asdict(goal), liquidity=budget, aversion=phi,
                behaviour=signals, sale_motives=[label for k, label in motives.items() if known(k) == "yes"],
                repeated_framing=matches("@inversion", values), declared_discrepancy=matches("@discord", values),
                existing_exposures=known("P05"), preferences=rules, mandatory_checks=blockers,
                pending=[k for k in active if known(k) is None],
                assumptions=dict(currency="CHF", same_day="withdrawals before contributions",
                                 uncertain_inflows="excluded from funding",
                                 aversion_model="mean–one-year variance on hypothetical bet"),
                provenance=dict(capital_chf=["F01"], horizon=["F02"], flows=["F03"],
                                capacity_loss_chf=["F04"], existing_exposures=["P05"],
                                sale_motives=["D01","D02","D03","D04"], liquidity=["F01","F02","F03"], aversion=["C01","C02","G00",*bounds],
                                goal=["F05","P01","P02",*(k for k in ["P03","P04"] if k in active)],
                                behaviour=list(signals), preferences=list(rules)))


@dataclass
class Interview:
    as_of: date
    answers: dict = field(default_factory=dict)
    history: list[Answer] = field(default_factory=list)
    versions: list[dict] = field(default_factory=list)
    confirmed: bool = False

    def record(self, key, value):
        if key not in route(self.answers):
            raise ValueError("Inactive card")
        value = validated(CARDS[key], value)
        if key in self.answers and self.answers[key] == value:
            return
        self.answers[key] = value
        self.history.append(Answer(key, value, datetime.now(timezone.utc).isoformat()))
        active = set(route(self.answers))
        self.answers = {k: v for k, v in self.answers.items() if k in active}
        self.confirmed = False

    def confirm(self):
        if any(k not in self.answers for k in route(self.answers)):
            raise ValueError("Complete or pass active cards before confirmation.")
        if not self.confirmed:
            self.versions.append(json.loads(json.dumps(dict(
                schema=1, bank=BANK["version"], version=len(self.versions)+1, as_of=self.as_of.isoformat(),
                confirmed_at=datetime.now(timezone.utc).isoformat(), answers=self.answers,
                changes=[asdict(a) for a in self.history], portrait=derive(self.answers,self.as_of),
                allocation_authorized=False))))
            self.confirmed = True
        return self.versions[-1]

    def save_risk(self, choice, *, accept, bills, comfort):
        from .risk_review import assess

        if not self.confirmed:
            raise ValueError("First confirm the corrected version of the portrait.")
        previous = self.versions[-1]
        review = assess(previous, choice, accept=accept, bills=bills, comfort=comfort)
        if previous.get("risk_review") == review:
            return previous
        saved = dict(previous, schema=2, version=len(self.versions) + 1,
                     portrait_version=review["portrait_version"], risk_review=review,
                     risk_saved_at=datetime.now(timezone.utc).isoformat())
        self.versions.append(json.loads(json.dumps(saved)))
        return self.versions[-1]


def read_version(raw):
    version = json.loads(raw)
    if not isinstance(version, dict) or version.get("schema") not in (1, 2):
        raise ValueError("Unknown schematic version")
    if not all(k in version for k in ("version","bank","portrait","answers","as_of")):
        raise ValueError("Incomplete version")
    if version["schema"] == 2 and "risk_review" not in version:
        raise ValueError("Risk decision absent")
    return version
