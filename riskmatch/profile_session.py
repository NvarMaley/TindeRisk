"""Replayable phase-one interviews. Only canonical responses can affect a score."""

import json
from copy import deepcopy
from math import isfinite
from pathlib import Path

from riskmatch import intake, profile, swipe

ROOT = Path(__file__).resolve().parents[1]
VERSION = "client-profile/1"
ROUTING = "adaptive-en/1"


def load_bank():
    bank = json.loads((ROOT / "questions/bank.json").read_text())
    transfer = json.loads((ROOT / "questions/transfer_validation.json").read_text())
    return bank, transfer


class Interview:
    def __init__(self, facts, seed, pilot=False):
        intake.validate_intake(facts)
        if type(seed) is not int or not 0 <= seed < 2**32 or type(pilot) is not bool:
            raise ValueError("Invalid interview assignment.")
        bank, transfer = load_bank()
        self.versions = [VERSION, ROUTING, bank["version"], transfer["version"]]
        self.cards = {c["id"]: c for c in bank["cards"]}
        self.transfer = transfer["items"]
        self.items = {**self.cards, **{c["id"]: c for c in self.transfer}}
        self.plan = profile.experimental_plan(self.cards, seed)
        self.initial = deepcopy(facts)
        self.facts = deepcopy(facts)
        self.pilot = pilot
        self.answers = {}
        self.checks = []
        self.frozen = []
        self.revised_after_freeze = False
        self.events = []
        self.confirmed = False
        self.stopped = False
        self.step = 0

    def current(self):
        if self.stopped:
            return "review", None
        key = profile.next_card(
            self.cards, self.answers, intake.mandate(self.facts), self.plan
        )
        if key:
            return "profile", key
        if len(self.checks) < len(self.frozen) and not self.revised_after_freeze:
            return "validation", self.frozen[len(self.checks)]["id"]
        return "review", None

    def _freeze(self):
        if not self.pilot or self.frozen or self.revised_after_freeze:
            return
        if self.current()[0] == "review" and any(
            k.startswith("S") for k in self.answers
        ):
            self.frozen = profile.validation_trials(
                self.cards, self.transfer, self.answers, self.plan
            )

    def statement(self):
        _, key = self.current()
        return swipe.prompt(
            self.items[key], self.display_order(key), self.step, self.facts
        )

    def apply(self, event):
        if not isinstance(event, dict):
            raise ValueError("Invalid interview event.")
        action = event.get("action")
        if action in ("answer", "swipe"):
            stage, key = self.current()
            fields = (
                {"action", "id", "seconds", "choice"}
                if action == "answer"
                else {"action", "id", "seconds", "direction", "step"}
            )
            if not key or event.get("id") != key or set(event) != fields:
                raise ValueError("The response is out of sequence.")
            seconds = event["seconds"]
            if action == "swipe":
                direction = event["direction"]
                if (
                    direction not in ("right", "left", "pass")
                    or type(event["step"]) is not int
                    or self.step != event["step"]
                ):
                    raise ValueError("Invalid swipe or statement order.")
                choice = self.statement()[direction]
            else:
                choice = event["choice"]
                if (
                    self.step
                    or type(choice) is not int
                    or not -1 <= choice < len(self.items[key]["answers"])
                ):
                    raise ValueError("That option is unavailable.")
            if (
                type(seconds) not in (float, int)
                or not isfinite(seconds)
                or seconds < 0
            ):
                raise ValueError("Invalid response time.")
            if choice is None:
                self.step += 1
                self.events.append(deepcopy(event))
                return
            self.step = 0
            if stage == "profile":
                self.answers[key] = choice
                self._freeze()
            else:
                self.checks.append(choice)
        elif action == "restart_card":
            if (
                set(event) != {"action", "id"}
                or self.current()[1] != event["id"]
                or not self.step
            ):
                raise ValueError("Only an active follow-up can be restarted.")
            self.step = 0
        elif action == "stop":
            stage, key = self.current()
            if (
                set(event) != {"action", "id"}
                or stage != "profile"
                or event["id"] != key
            ):
                raise ValueError("Only the active questionnaire can be ended early.")
            self.stopped = True
        elif action == "resume":
            if set(event) != {"action"} or not self.stopped:
                raise ValueError("There is no early stop to resume.")
            self.stopped = self.confirmed = False
            self.revised_after_freeze |= self.pilot
        elif action == "confirm":
            if (
                set(event) != {"action"}
                or self.current()[0] != "review"
                or self.confirmed
            ):
                raise ValueError(
                    "Only a completed, unconfirmed profile can be confirmed."
                )
            self.confirmed = True
        elif action == "revise":
            key = event.get("id")
            if (
                set(event) != {"action", "id"}
                or not isinstance(key, str)
                or key not in self.answers
            ):
                raise ValueError("Choose an answered profile card to revise.")
            self._invalidate()
            for old in list(self.answers)[list(self.answers).index(key) :]:
                del self.answers[old]
        elif action == "facts":
            if set(event) != {"action", "facts"}:
                raise ValueError("Invalid factual correction.")
            facts = event["facts"]
            intake.validate_intake(facts)
            if facts != self.facts:
                self._invalidate()
                currency_changed = any(
                    self.facts[k] != facts[k] for k in ("currency", "other_currency")
                )
                self.facts = deepcopy(facts)
                # Retain only the still-valid prefix. A changed branch must be answered anew.
                old, self.answers = self.answers, {}
                for k, v in old.items():
                    if self.current() != ("profile", k) or (
                        k == "F07" and currency_changed
                    ):
                        break
                    self.answers[k] = v
                self._freeze()
        else:
            raise ValueError("Unknown interview event.")
        self.events.append(deepcopy(event))

    def _invalidate(self):
        self.step = 0
        feedback_seen = self.pilot and self.current()[0] == "review"
        self.confirmed = self.stopped = False
        if self.frozen or feedback_seen:
            self.revised_after_freeze = True
        self.frozen = []
        self.checks = []

    def display_order(self, key):
        count = len(self.items[key]["answers"])
        if key.startswith(("A", "L", "V")):
            return profile.sides(key, self.plan["seed"]) + list(range(2, count))
        return list(range(count))

    def report(self):
        stage, _ = self.current()
        score = profile.summary(self.cards, self.answers)
        if self.stopped:
            score.update(
                lo=None,
                hi=None,
                bands=[],
                reason="Interview ended before the common and adaptive route was complete",
            )
        core = {k: v for k, v in self.answers.items() if self.cards[k]["core"]}
        checks = []
        for i, item in enumerate(self.frozen):
            choice = self.checks[i] if i < len(self.checks) else None
            predicted = item["prediction"]
            checks.append(
                dict(
                    **item,
                    choice=choice,
                    side_order=self.display_order(item["id"]),
                    agreement=(choice == predicted)
                    if choice in (0, 1) and predicted is not None
                    else None,
                )
            )
        # Answers and evidence are reproducible from the event sequence, including discarded routes.
        return dict(
            status="ended_early" if self.stopped else stage,
            confirmed=self.confirmed,
            tolerance=score,
            capacity=intake.assess(self.facts, self.answers),
            core_tolerance=profile.summary(self.cards, core),
            answers=dict(self.answers),
            completion=len(self.answers),
            holdouts=checks,
            common_order=self.plan["order"],
            held_out_ids=self.plan["reserve"],
            revised_after_freeze=self.revised_after_freeze,
            elapsed_answer_seconds=sum(
                e["seconds"] for e in self.events if e["action"] in ("answer", "swipe")
            ),
            swipe_count=sum(e["action"] == "swipe" for e in self.events),
            presented_options={
                e["id"]: self.display_order(e["id"])
                for e in self.events
                if e["action"] == "answer"
            },
        )

    def dump(self):
        # Drafts can be resumed without disclosing the estimated score or held-out predictions.
        stage, _ = self.current()
        result = (
            self.report()
            if stage == "review"
            else {"status": stage, "answered": len(self.answers)}
        )
        return json.dumps(
            dict(
                presentation="statement-swipe/1",
                versions=self.versions,
                seed=self.plan["seed"],
                pilot=self.pilot,
                initial=self.initial,
                events=self.events,
                result=result,
            ),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    @classmethod
    def restore(cls, payload):
        if not isinstance(payload, (str, bytes)) or len(payload) > 1_000_000:
            raise ValueError("The profile file is too large or invalid.")
        try:
            data = json.loads(payload)
            session = cls(data["initial"], data["seed"], data["pilot"])
            legacy = session.versions.copy()
            legacy[2] = "1.0-pilot-en"
            previous = data["versions"] == legacy and "presentation" not in data
            if data.get("presentation") not in (None, "statement-swipe/1") or (
                data["versions"] != session.versions and not previous
            ):
                raise ValueError(
                    "This export uses a different questionnaire or routing version."
                )
            if not isinstance(data["events"], list) or len(data["events"]) > 2500:
                raise ValueError("Invalid interview history.")
            for event in data["events"]:
                session.apply(event)
        except (
            KeyError,
            TypeError,
            RecursionError,
            UnicodeError,
            OverflowError,
        ) as error:
            raise ValueError("Invalid profile file.") from error
        return session
