"""Participant-level checks for the profile pilot. Inputs are local, voluntary exports."""

from collections import Counter, defaultdict
from datetime import date
from random import Random
from statistics import median

from riskmatch.profile import validation_trials


def _interval(clusters, draws, seed):
    """Percentile interval for paired accuracy differences, resampling entire people."""
    if len(clusters) < 2:
        return None
    rng = Random(seed)
    differences = []
    for _ in range(draws):
        sample = rng.choices(clusters, k=len(clusters))
        differences.append(sum(x for x, n in sample) / sum(n for x, n in sample))
    differences.sort()
    return [differences[int((draws - 1) * q)] for q in (0.025, 0.975)]


def evaluate(participants, draws=1000, seed=43):
    """One record per invited person: id, split (baseline/evaluation), first, retest.

    Visits hold Interview objects or None for missing exports. Use the recorded split
    established before responses. Use completed first-visit routes without post-feedback revisions. Supply ISO
    first_date/retest_date for the seven-day agreement table.
    """
    if draws < 2:
        raise ValueError("At least two bootstrap draws are required.")
    ids = [p["id"] for p in participants]
    if len(set(ids)) != len(ids) or any(
        p["split"] not in ("baseline", "evaluation") for p in participants
    ):
        raise ValueError("Use one row per participant and a prespecified split.")
    votes = defaultdict(Counter)

    def usable(s):
        return (
            s
            and s.pilot
            and bool(s.frozen)
            and len(s.checks) == 4
            and not s.revised_after_freeze
        )

    for p in participants:
        s = p["first"]
        if p["split"] == "baseline" and usable(s):
            for trial, choice in zip(s.frozen, s.checks, strict=True):
                if choice in (0, 1):
                    votes[trial["id"]][choice] += 1
    # Ties and unseen items abstain. The same participant cannot train and test the benchmark.
    baseline = {
        k: int(count[1] > count[0])
        for k, count in votes.items()
        if count[1] != count[0]
    }
    status = Counter()
    times, counts, transitions = [], [], Counter()
    metrics = {"reserved": Counter(), "transfer": Counter()}
    clusters = {family: [] for family in metrics}
    for p in participants:
        if p["split"] != "evaluation":
            continue
        s = p["first"]
        status["invited"] += 1
        if s is None:
            status["no_first_export"] += 1
            continue
        report = s.report()
        status[report["status"]] += 1
        if not usable(s):
            status["ineligible_for_prediction_check"] += 1
            continue
        status["eligible"] += 1
        times.append(report["elapsed_answer_seconds"])
        counts.append(len(s.answers))
        take = {k: v for k, v in s.answers.items() if s.cards[k]["core"]}
        core = validation_trials(s.cards, s.transfer, take, s.plan)
        differences = defaultdict(list)
        for frozen, simple, choice in zip(s.frozen, core, s.checks, strict=True):
            key = frozen["id"]
            family = "transfer" if key.startswith("V") else "reserved"
            tally = metrics[family]
            tally["planned"] += 1
            tally["binary_choices"] += choice in (0, 1)
            for name, guess in [
                ("adaptive", frozen["prediction"]),
                ("core", simple["prediction"]),
                ("baseline", baseline.get(key)),
            ]:
                if guess is not None:
                    tally[name + "_predictions"] += 1
                    if choice in (0, 1):
                        tally[name + "_comparable"] += 1
                        tally[name + "_correct"] += guess == choice
            if (
                choice in (0, 1)
                and frozen["prediction"] is not None
                and key in baseline
            ):
                differences[family].append(
                    int(frozen["prediction"] == choice) - int(baseline[key] == choice)
                )
        for family, diff in differences.items():
            clusters[family].append((sum(diff), len(diff)))
        retest = p.get("retest")
        if retest is None:
            status["no_retest_export_among_eligible"] += 1
        elif usable(retest) and s.facts == retest.facts:
            if not p.get("first_date") or not p.get("retest_date"):
                status["retest_timing_unknown"] += 1
                continue
            gap = date.fromisoformat(p["retest_date"]) - date.fromisoformat(
                p["first_date"]
            )
            if gap.days != 7:
                status["retest_outside_day_seven"] += 1
                continue
            before = " / ".join(report["tolerance"]["bands"]) or "Undetermined"
            after = " / ".join(retest.report()["tolerance"]["bands"]) or "Undetermined"
            transitions[(before, after)] += 1
        else:
            status["changed_mandate_or_incomplete_retest"] += 1
    results = {}
    for family, tally in metrics.items():
        samples = clusters[family]
        scores = {}
        for method in ("adaptive", "core", "baseline"):
            n = tally[method + "_comparable"]
            scores[method] = dict(
                coverage=tally[method + "_predictions"] / tally["planned"]
                if tally["planned"]
                else None,
                agreement=tally[method + "_correct"] / n if n else None,
                comparable=n,
            )
        results[family] = dict(
            counts=dict(tally),
            scores=scores,
            paired_people=len(samples),
            paired_accuracy_gain=sum(x for x, n in samples) / sum(n for x, n in samples)
            if samples
            else None,
            paired_95pct_interval=_interval(samples, draws, seed),
        )
    return dict(
        participants=dict(status),
        predictions=results,
        median_profile_cards=median(counts) if counts else None,
        median_answer_seconds=median(times) if times else None,
        retest_transitions=[
            dict(first=a, retest=b, count=n)
            for (a, b), n in sorted(transitions.items())
        ],
    )
