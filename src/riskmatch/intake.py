"""Factual mandate, dated liquidity and terminal goal in the spending currency."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from math import exp, expm1, isfinite, log, log1p
import re

from scipy.optimize import brentq


@dataclass(frozen=True)
class Answer:
    state: str
    low: float | None = None
    high: float | None = None


def amount(raw, *, percent=False):
    value = raw.strip().lower()
    states = {"": "missing", "?": "unknown", "pass": "declined"}
    if value in states:
        return Answer(states[value])
    parts = re.split(r"\s*\.\.\s*", value)
    if len(parts) > 2:
        raise ValueError("Enter one number or a range such as 10000..15000.")
    try:
        bounds = [float(p) for p in parts]
    except ValueError:
        raise ValueError(
            "Use numbers without thousands separators, ? or pass."
        ) from None
    if not all(isfinite(x) for x in bounds) or bounds[-1] < bounds[0]:
        raise ValueError("Use finite numbers with the lower amount first.")
    if percent and bounds[0] <= -100 or not percent and bounds[0] < 0:
        raise ValueError(
            "Rates must exceed −100%."
            if percent
            else "Amounts must be zero or positive."
        )
    return Answer("known", bounds[0], bounds[-1])


@dataclass(frozen=True)
class Flow:
    day: date
    kind: str
    value: Answer
    confirmed: bool = True


def ladder(start, capital, buffer, flows, adverse, delay_days=0):
    """Opening reserve funds the peak cumulative deficit. Same-day cash settles before payment."""
    cap = capital.low if adverse else capital.high
    safety = buffer.high if adverse else buffer.low
    totals = defaultdict(lambda: [0.0, 0.0])
    totals[start]
    for flow in flows:
        if flow.kind == "withdrawal":
            totals[flow.day][1] += flow.value.high if adverse else flow.value.low
        elif flow.kind == "bill funding" and flow.confirmed:
            totals[flow.day + timedelta(days=delay_days)][0] += (
                flow.value.low if adverse else flow.value.high
            )
    gap = peak = 0.0
    rows = []
    first = None
    for day, (income, expense) in sorted(totals.items()):
        gap += expense - income
        peak = max(peak, gap)
        shortage = max(0.0, safety + gap - cap)
        # The emergency buffer must already be available at the opening instant.
        if day == start:
            shortage = max(shortage, safety - cap)
        if shortage and first is None:
            first = day.isoformat()
        rows.append(
            dict(
                date=day.isoformat(),
                settled=income,
                due=expense,
                cumulative_gap=gap,
                shortfall=shortage,
            )
        )
    required = safety + peak
    return dict(
        required=required,
        protected=min(cap, required),
        investable=max(0.0, cap - required),
        shortfall=max(0.0, required - cap),
        first_shortfall=first,
        rows=rows,
    )


def funding_rate(start, end, initial, contributions, target):
    """Solve in log-growth space; only positive investments before maturity earn a return."""
    years = (end - start).days / 365
    if years <= 0:
        raise ValueError("The goal date must follow the start date.")
    floor = sum(v for day, v in contributions if day == end)
    terms = [(years, initial)] + [
        ((end - day).days / 365, v) for day, v in contributions if day < end
    ]
    terms = [(t, v) for t, v in terms if v > 0]
    if not terms:
        return {"status": "any rate" if target == floor else "no solution"}
    if target <= floor:
        return {"status": "no finite rate"}

    # log(sum(v * exp(t*x))) is monotone. Centering avoids overflow in the root search.
    def residual(x):
        logs = [log(v) + t * x for t, v in terms]
        top = max(logs)
        return top + log(sum(exp(y - top) for y in logs)) - log(target - floor)

    lo, hi = -1.0, 1.0
    while residual(lo) > 0:
        lo *= 2
    while residual(hi) < 0:
        hi *= 2
    x = brentq(residual, lo, hi, xtol=1e-14)
    if x > 700 or x < -36:
        return {"status": "rate outside numerical reporting range"}
    rate = expm1(x)
    terminal = floor + sum(exp(log(v) + t * x) for t, v in terms)
    return dict(status="solved", rate=rate, terminal=terminal, target=target)


def evaluate(draft):
    """Validate field by field; missing goal inputs need not block liquidity calculations."""
    issues = {}

    def read(label, text, percent=False):
        try:
            return amount(text, percent=percent)
        except ValueError as exc:
            issues[label] = str(exc)
            return Answer("invalid")

    fields = {
        key: read(key, draft.get(key, ""), key in ("desired", "inflation"))
        for key in ("capital", "buffer", "target", "desired", "inflation")
    }
    start, end = draft.get("start"), draft.get("end")
    if start and end and end <= start:
        issues["end"] = "Choose a goal date after the start date."
    flows, incomplete = [], set()
    for i, row in enumerate(draft.get("flows", []), 1):
        kind, day = row["kind"], row["day"]
        ans = read(f"Flow {i} amount", row["amount"])
        if day and ((start and day < start) or (end and day > end)):
            issues[f"Flow {i} date"] = "Use a settlement date within the mandate."
        if not day or ans.state != "known":
            if kind == "withdrawal" or row["confirmed"]:
                incomplete.add(kind)
        elif kind not in ("withdrawal", "bill funding", "goal deposit"):
            issues[f"Flow {i} type"] = "Unknown cash flow type."
        else:
            flows.append(Flow(day, kind, ans, row["confirmed"]))
    result = dict(issues=issues, fields=fields, capacity=None, rates=None)
    if (
        any(k not in ("desired", "target", "inflation") for k in issues)
        or not start
        or not draft.get("currency")
        or (
            draft.get("currency") == "Other"
            and not draft.get("currency_name", "").strip()
        )
        or any(fields[k].state != "known" for k in ("capital", "buffer"))
        or draft.get("bill_list") != "Complete"
        or incomplete & {"withdrawal", "bill funding"}
    ):
        return result
    cap = [
        ladder(start, fields["capital"], fields["buffer"], flows, adverse)
        for adverse in (False, True)
    ]
    result.update(
        capacity=cap,
        delayed=ladder(start, fields["capital"], fields["buffer"], flows, True, 30),
    )
    today_money = draft.get("basis") == "Today's purchasing power"
    if (
        not end
        or fields["target"].state != "known"
        or (today_money and fields["inflation"].state != "known")
        or draft.get("goal_list") != "Complete"
        or "goal deposit" in incomplete
    ):
        return result
    rates = []
    for adverse, case in zip((False, True), cap):
        if case["shortfall"]:
            rates.append(dict(status="withdrawal funding shortfall"))
            continue
        target = fields["target"].high if adverse else fields["target"].low
        if today_money:
            inflation = fields["inflation"].high if adverse else fields["inflation"].low
            try:
                target *= exp((end - start).days / 365 * log1p(inflation / 100))
            except OverflowError:
                target = float("inf")
        if not isfinite(target):
            rates.append(dict(status="target outside numerical reporting range"))
            continue
        deposits = [
            (f.day, f.value.low if adverse else f.value.high)
            for f in flows
            if f.kind == "goal deposit" and f.confirmed
        ]
        rates.append(funding_rate(start, end, case["investable"], deposits, target))
    result["rates"] = rates
    return result
