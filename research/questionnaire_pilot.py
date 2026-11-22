"""Frozen paired predictions and per-route metrics for synthetic interviews."""

from hashlib import sha256
import json
from pathlib import Path
from random import Random
from statistics import mean

from riskmatch.interview import CORE, current, report, threshold

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = json.loads((ROOT / "questions/pilot_holdout_v1.json").read_text())["items"]
IDS = tuple(c["id"] for c in HOLDOUT)


def partition(pid):
    # Assigned once before the first response; all visits share the same pseudonym.
    number = int.from_bytes(sha256(("pilot-v1/" + pid).encode()).digest()[:8], "big")
    return "development" if number % 3 == 0 else "evaluation"


def predictions(answers):
    r = report(answers)
    out = {}
    for card in HOLDOUT:
        boundary = threshold(card)
        if r["status"] not in ("bounded", "one-sided"):
            choice = None
        elif r["low"] > boundary:
            choice = "sure"
        elif r["high"] is not None and r["high"] < boundary:
            choice = "gamble"
        else:
            choice = None
        out[card["id"]] = choice
    return out


def freeze(log):
    # The first completed core is sealed. Later corrections affect the adaptive arm only.
    end = next(
        (
            n
            for n, event in enumerate(log, 1)
            if event["kind"] == "answer"
            and event["id"] == CORE[-1]
            and set(CORE) <= current(log[:n]).keys()
        ),
        len(log),
    )
    core = {i: v for i, v in current(log[:end]).items() if i in CORE or i == "P01"}
    active = current(log)
    return {"core": predictions(core), "adaptive": predictions(active)}


def participant(pid, frozen, observations):
    """An assigned participant always contributes four slots, even after dropout."""
    if set(observations) - set(IDS) or any(
        x not in ("sure", "gamble", "unsure", None) for x in observations.values()
    ):
        raise ValueError("Unexpected validation answer")
    row = {"id": pid, "partition": partition(pid)}
    for arm, preds in frozen.items():
        if set(preds) != set(IDS) or any(
            x not in ("sure", "gamble", None) for x in preds.values()
        ):
            raise ValueError("Incomplete prediction snapshot")
        available = [i for i in IDS if preds[i] is not None]
        paired = [i for i in available if observations.get(i) in ("sure", "gamble")]
        hits = sum(preds[i] == observations[i] for i in paired)
        row[arm] = {
            "predicted": len(available),
            "verified": len(paired),
            "hits": hits,
            "coverage": len(available) / 4,
            "agreement": hits / len(paired) if paired else None,
            "low": hits / 4,
            "high": (hits + 4 - len(paired)) / 4,
        }
    common = [
        i
        for i in IDS
        if frozen["core"][i]
        and frozen["adaptive"][i]
        and observations.get(i) in ("sure", "gamble")
    ]
    row["common_items"] = len(common)
    row["paired_agreement_gain"] = (
        mean(
            int(frozen["adaptive"][i] == observations[i])
            - int(frozen["core"][i] == observations[i])
            for i in common
        )
        if common
        else None
    )
    row["coverage_gain"] = row["adaptive"]["coverage"] - row["core"]["coverage"]
    row["verified_hits_gain"] = (row["adaptive"]["hits"] - row["core"]["hits"]) / 4
    return row


def paired_interval(rows, key, seed=2302, draws=2000):
    values = [r[key] for r in rows if r[key] is not None]
    if not values:
        return {"participants": 0, "mean": None, "interval": None}
    rng = Random(seed)
    estimates = sorted(mean(rng.choices(values, k=len(values))) for _ in range(draws))
    return {
        "participants": len(values),
        "mean": mean(values),
        "interval": [estimates[int(0.025 * draws)], estimates[int(0.975 * draws) - 1]],
    }


def summarize(rows):
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("One row per participant required")
    if not rows:
        return {"assigned": 0}
    out = {"assigned": len(rows)}
    for arm in ("core", "adaptive"):
        verified = [
            r[arm]["agreement"] for r in rows if r[arm]["agreement"] is not None
        ]
        out[arm] = {
            "coverage": mean(r[arm]["coverage"] for r in rows),
            "verified_people": len(verified),
            "agreement": mean(verified) if verified else None,
            "all_assigned_bounds": [
                mean(r[arm][k] for r in rows) for k in ("low", "high")
            ],
        }
    for key in ("paired_agreement_gain", "coverage_gain", "verified_hits_gain"):
        out[key] = paired_interval(rows, key)
    return out
