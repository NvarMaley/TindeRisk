"""Structural exercises and simulated participants; no personal or market data."""

import argparse
import csv
from collections import Counter
import json
from pathlib import Path
from random import Random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riskmatch.interview import (
    CARDS,
    CORE,
    MAX_CARDS,
    threshold,
    current,
    eligible,
    report,
    submit,
)
from questionnaire_pilot import HOLDOUT, IDS, freeze, participant, summarize

KINDS = (
    "consistent",
    "contradictory",
    "indifferent",
    "pass-heavy",
    "always yes",
    "random",
    "stake-dependent",
    "early stop",
)
SEED = 2301


def economic_choice(card, phi):
    # Independent expected-utility calculation from end balances.
    returns = [
        (balance - card["stake"]) / card["stake"] for balance in card["outcomes"]
    ]
    mean = sum(p * x for p, x in zip(card["probabilities"], returns))
    variance = sum(p * (x - mean) ** 2 for p, x in zip(card["probabilities"], returns))
    return (
        "sure"
        if card["certain"] / card["stake"] - 1 >= mean - phi * variance / 2
        else "gamble"
    )


def response(i, kind, rng, phi):
    c = CARDS[i]
    if kind == "always yes":
        return "yes"
    if kind == "random":
        return rng.choice(["yes", "no", "pass"])
    if i in ("C01", "P01"):
        return "yes" if i == "C01" else "no"
    if kind == "pass-heavy" and rng.random() < 0.8:
        return "pass"
    if c["effect"] == "bound":
        if kind == "indifferent":
            return "pass"
        if kind == "contradictory" and i in ("C03", "C05"):
            return "yes" if i == "C03" else "no"
        choice = economic_choice(c, phi)
        return next(a for a, value in c["answers"].items() if value == choice)
    return rng.choice(["yes", "no", "pass"])


def simulate(kind, index, form):
    rng = Random(SEED + 10000 * KINDS.index(kind) + index)
    phi = rng.uniform(0.2, 8)
    log = []
    limit = rng.randrange(0, 15) if kind == "early stop" else MAX_CARDS
    while len(log) < limit and (pool := eligible(current(log), form)):
        i = pool[0]
        a = response(i, kind, rng, phi)
        rev = len(log)
        assert submit(log, i, a, "simulation", rev, form)
        assert not submit(log, i, a, "simulation", rev, form)
    active = current(log)
    if kind == "early stop":
        log.append(dict(kind="stop", step=len(active)))
    else:
        assert not eligible(active, form)
    assert len(active) <= MAX_CARDS and sum(i.startswith("T") for i in active) <= 2
    if kind == "consistent" and report(active)["used"]:
        res = report(active)
        assert res["low"] <= phi and (res["high"] is None or phi <= res["high"])
    frozen = freeze(log)
    observations = {}
    for item in HOLDOUT:
        if kind == "early stop":
            continue
        if kind == "random":
            choice = rng.choice(["sure", "gamble", "unsure"])
        elif kind == "always yes":
            choice = "sure" if IDS.index(item["id"]) % 2 == 0 else "gamble"
        elif kind == "indifferent" or (kind == "pass-heavy" and rng.random() < 0.8):
            choice = "unsure"
        else:
            choice = economic_choice(
                item, phi * (item["stake"] / 1000 if kind == "stake-dependent" else 1)
            )
        observations[item["id"]] = choice
    row = participant(f"sim-{kind}-{index:04d}", frozen, observations)
    r = report(active)
    row.update(
        kind=kind,
        form=form,
        route=list(active),
        status=r["status"],
        stopped=kind == "early stop",
        unresolved=r["status"]
        in ("conflict", "insufficient", "comprehension unresolved")
        or len(r["options"]) != 1
        or bool(r["sensitive"]),
        frozen=frozen,
        observations=observations,
    )
    return row


def witnesses():
    # Force rare trigger combinations without mixing these traces into prevalence counts.
    routes = []
    for focus in list(CARDS):
        log = []
        wants = {"C01": "yes", "C12": "no", "C13": "no", "C14": "yes", "C15": "yes"}

        def activate(i):
            c = CARDS[i]
            if i == "P01":
                wants["C01"] = "pass"
                wants["P01"] = "no"
            if i.startswith("T"):
                wants.update({k: "pass" for k in CORE if CARDS[k]["effect"] == "bound"})
                wants[
                    "C05" if threshold(CARDS[i]) > threshold(CARDS["C05"]) else "C04"
                ] = "yes"
            if not i.startswith("B"):
                return
            trig = c["trigger"]
            if trig == "loss pattern":
                wants.update(C08="no", C09="no", C10="yes", C11="yes")
            elif trig == "sensitive":
                wants.update(C03="yes", C05="no")
            else:
                parent, value = trig.split("|")[0].split(":")
                activate(parent)
                wants[parent] = value

        activate(focus)
        form = int(focus[1:]) - 1 if focus.startswith("T") else 0
        while pool := eligible(current(log), form):
            i = pool[0]
            submit(log, i, wants.get(i, "no"), "witness", len(log), form)
            if i == focus:
                break
        routes.append(list(current(log)))
    return routes


def run(per_kind):
    rows = [simulate(k, i, i % 20) for k in KINDS for i in range(per_kind)]
    counts = Counter(i for r in rows for i in r["route"])
    targeted = witnesses()
    coverage = {
        i: {"generated": counts[i], "witness": sum(i in path for path in targeted)}
        for i in CARDS
    }
    missing = [i for i, c in coverage.items() if not any(c.values())]
    summary = {
        "seed": SEED,
        "simulations": len(rows),
        "missing": missing,
        "coverage": coverage,
        "behaviors": {},
    }
    for k in KINDS:
        group = [r for r in rows if r["kind"] == k]
        summary["behaviors"][k] = {
            "n": per_kind,
            "unresolved": sum(r["unresolved"] for r in group),
            "early_stops": sum(r["stopped"] for r in group),
            "status": dict(Counter(r["status"] for r in group)),
        }
    summary["synthetic_evaluation"] = summarize(
        [r for r in rows if r["partition"] == "evaluation"]
    )
    return rows, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rows", type=Path, help="Write the generated participant table as JSON lines"
    )
    parser.add_argument(
        "--table",
        type=Path,
        help="Write one synthetic row per assigned participant as CSV",
    )
    args = parser.parse_args()
    rows, summary = run(60)
    if args.rows:
        args.rows.write_text("".join(json.dumps(row) + "\n" for row in rows))
    if args.table:
        with args.table.open("w", newline="") as stream:
            columns = [
                "id",
                "partition",
                "kind",
                "form",
                "route",
                "status",
                "unresolved",
                "stopped",
                "core_predicted",
                "core_verified",
                "core_hits",
                "adaptive_predicted",
                "adaptive_verified",
                "adaptive_hits",
                "common_items",
            ]
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                flat = {k: row[k] for k in columns if k in row}
                flat["route"] = " ".join(row["route"])
                for arm in ("core", "adaptive"):
                    for k in ("predicted", "verified", "hits"):
                        flat[arm + "_" + k] = row[arm][k]
                writer.writerow(flat)
    print(json.dumps(summary, indent=2))
    if summary["missing"]:
        raise SystemExit("Unreached cards: " + str(summary["missing"]))
