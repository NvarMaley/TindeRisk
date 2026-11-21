"""Pilot questionnaire. Answer indices are independent of the displayed side."""
from math import inf, isclose, isfinite
from random import Random
from statistics import median

from riskmatch.mandate import capacity, required_rate

CORE = "A01 L01 B01 A02 L03 A03 B02 A04 L02 A05 A06 L04 A07 A08".split()
BANDS = [(0, 2, "Very high"), (2, 5, "High"), (5, 10, "Moderate"), (10, inf, "Low")]


def experimental_plan(cards, seed):
    rng = Random(seed)
    reserve = rng.sample([k for k in cards if k.startswith("A") and not cards[k]["core"]], 2)
    # Two sequences interspersed, while maintaining a distance between the elements of each pair.
    order = CORE if seed % 2 == 0 else "A08 L03 B02 A07 L01 A06 B01 A05 L04 A04 A03 L02 A02 A01".split()
    return dict(reserve=reserve, order=order, seed=seed)


def sides(key, seed):
    reverse = Random(f"{seed // 2}-{key}").randrange(2) ^ (seed % 2)
    return [1, 0] if reverse else [0, 1]


def choice_threshold(stake, certain, outcomes, probabilities):
    if (not outcomes or len(outcomes) != len(probabilities) or
            not all(isfinite(x) for x in (stake, certain, *outcomes, *probabilities)) or
            stake <= 0 or not isclose(sum(probabilities), 1) or min(probabilities) < 0):
        raise ValueError("Invalid amounts or probabilities")
    returns = [x / stake - 1 for x in outcomes]
    mean = sum(p*r for p,r in zip(probabilities, returns, strict=True))
    var = sum(p*(r-mean)**2 for p,r in zip(probabilities, returns))
    if var <= 0 or certain <= min(outcomes) or certain >= max(outcomes):
        raise ValueError("Trade-off cannot distinguish preferences (variance or dominance)")
    return 2*(mean - (certain / stake - 1))/var


def aversion_range(cards, answers):
    lo, hi, count = 0., inf, 0
    for key, choice in answers.items():
        if not key.startswith("A") or choice not in (0, 1, 2):
            continue
        threshold = cards[key]["phi_threshold"]
        if choice in (0, 2):
            lo = max(lo, threshold * (.9 if choice == 2 else 1))
        if choice in (1, 2):
            hi = min(hi, threshold * (1.1 if choice == 2 else 1))
        count += 1
    return lo, hi, count


def loss_pairs(answers):
    return sum(answers.get(f"L{i:02}") == 1 and answers.get(f"L{i+1:02}") == 0
               for i in range(1, 14, 2))


def next_card(cards, answers, mandate, plan):
    for key in ("C1", "C2"):
        if key not in answers:
            return key
        if answers[key] == cards[key]["answers"].index(cards[key]["correct"]):
            break
    else:
        return None
    for key in plan["order"]:
        if key not in answers:
            return key
    lo, hi, _ = aversion_range(cards, answers)
    probes = [k for k in answers if k.startswith("A") and not cards[k]["core"]]
    candidates = [k for k,c in cards.items() if k.startswith("A") and not c["core"]
                  and k not in answers and k not in plan["reserve"]
                  and lo < c["phi_threshold"] < hi]
    unresolved_band = any(lo < boundary <= hi for boundary, _, _ in BANDS[1:])
    open_edge = lo == 0 or not isfinite(hi)
    if (unresolved_band or open_edge) and candidates and len(probes) < 2:
        center = (lo+hi)/2 if isfinite(hi) else median(cards[k]["phi_threshold"] for k in candidates)
        return min(candidates, key=lambda k: abs(cards[k]["phi_threshold"]-center))
    if loss_pairs({k: answers.get(k) for k in ("L01","L02","L03","L04")}) == 1:
        # Match the conditional pair to the stake and rotate equally sized variants.
        capital = mandate["capital"] or 0
        pair = 9 if capital >= 15000 else (5,11)[plan["seed"] % 2] if capital >= 7500 else (7,13)[plan["seed"] % 2]
        for i in (pair, pair+1):
            key = f"L{i:02}"
            if key not in answers:
                return key
    a, m = answers, mandate
    goal_needs_review = False
    if m["goal"]:
        available = capacity(m, a)["free"]
        rate = required_rate(available, m["contribution"], m["horizon"], m["goal"])
        goal_needs_review = m["wish"] is None or rate is None or rate > m["wish"]/100
    branches = [
        ("B03", a.get("B01")==1), ("B04", a.get("B03")==1), ("B05", a.get("B01")==2),
        ("B06", a.get("B02")==1), ("B07", a.get("B01")==0), ("B08", a.get("B02")==0),
        ("B09", loss_pairs(a)>=2), ("B10", a.get("B01")==1 and a.get("B02")==2),
        ("F01", m["withdraw"] != 0 or a.get("B03")==0), ("F02", bool(m["withdraw"])),
        ("F03", m["household"]!="Covered elsewhere"), ("F04", m["variable"]),
        ("F05", m["employer"]), ("F06", bool(m["ethics"])), ("F07", m["currency"]!="CHF"),
        ("F08", goal_needs_review),
    ]
    for key, condition in branches:
        if condition and key not in a:
            return key
    closing = next(key for key,condition in [
        ("S01",bool(m["withdraw"])),("S02",a.get("B09")==0),("S03",a.get("B01")==2),
        ("S04",m["variable"]),("S05",m["strict"] or a.get("F06")==0),("S06",True)] if condition)
    return closing if closing not in a else None


def summary(cards, answers):
    lo, hi, count = aversion_range(cards, answers)
    reason = "Too few understood choices" if count < 2 else "Inconsistent trade-offs" if lo > hi else ""
    bands = [] if reason else [s for l,h,s in BANDS if lo < h and hi >= l]
    follow = next((cards[k]["answers"][v] for k,v in answers.items() if k.startswith("S") and v >= 0), None)
    observation = None
    if loss_pairs(answers) >= 2 and answers.get("B09") == 0:
        observation = "In two comparisons, you preferred the certain amount when a loss on your initial stake became possible. You confirmed this interpretation."
    return dict(lo=None if reason else lo, hi=None if reason or not isfinite(hi) else hi,
                n=count, bands=bands, reason=reason, follow=follow, observation=observation)


def validation_trials(cards, transfer, answers, plan):
    result = []
    bounds = summary(cards, answers)
    # Two matching pairs, alternated by participant number in the test run.
    ids = [0, 2] if plan["seed"] % 2 == 0 else [1, 3]
    for key in plan["reserve"] + [transfer[i]["id"] for i in ids]:
        if key in cards:
            c = cards[key]
            threshold = c["phi_threshold"]
        else:
            c = next(t for t in transfer if t["id"] == key)
            threshold = choice_threshold(c["stake_CHF"], c["certain_CHF"], c["outcomes_CHF"], c["probabilities"])
        prediction = None
        if bounds["lo"] is not None:
            if bounds["lo"] > threshold:
                prediction = 0
            elif bounds["hi"] is not None and bounds["hi"] < threshold:
                prediction = 1
        result.append(dict(id=key, prediction=prediction))
    return result
