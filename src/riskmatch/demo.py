"""Project-authored portable mandate and alternatives."""

from datetime import date
import numpy as np
from .intake import evaluate
from .reviews import COV, MU


def mandate():
    return dict(
        start=date(2026, 11, 23),
        end=date(2034, 11, 23),
        goal="Fictional eight-year goal",
        currency="CHF",
        target="65000",
        basis="Today's purchasing power",
        inflation="2",
        capital="50000",
        buffer="0",
        bill_list="Complete",
        goal_list="Complete",
        exclusions="",
        flows=[
            dict(
                id=0,
                kind="withdrawal",
                day=date(2027, 11, 23),
                amount="15000",
                confirmed=True,
            )
        ],
    )


def matches(d):
    expected = mandate()
    e = evaluate(d)
    if e["issues"] or not e["capacity"] or e["capacity"][1]["shortfall"] > 0:
        return False
    return all(
        d.get(k) == expected[k]
        for k in ["start", "end", "currency", "basis", "bill_list", "goal_list"]
    ) and (
        not d.get("exclusions")
        and len(d["flows"]) == 1
        and d["flows"][0]["kind"] == "withdrawal"
        and d["flows"][0]["day"] == expected["flows"][0]["day"]
        and d["flows"][0]["amount"] == "15000"
        and d.get("capital") == "50000"
        and d.get("buffer") == "0"
        and d.get("inflation") == "2"
        and d.get("target") == "65000"
    )


def allocations(cap):
    data = {}
    for name, shape in [
        ("Diversified mix", np.array([0.45, 0.3, 0.1])),
        ("Bond-heavy mix", np.array([0.20, 0.55, 0.1])),
    ]:
        weights = shape * min(1, cap / np.sqrt(shape @ COV @ shape))
        fee = weights.sum() * 35000 * 0.001
        data[name] = (weights.tolist(), fee, 35000 * (1 - weights.sum()) - fee)
    return data


def difference_interval(data):
    """Two-sided illustrative normal interval, assuming three independent years."""
    first, second = data.values()
    delta = np.array(first[0]) - np.array(second[0])
    mean = float(delta @ MU - (first[1] - second[1]) / 35000)
    width = 1.96 * np.sqrt(delta @ COV @ delta / 3)
    return mean - width, mean + width
