"""Client studio transport and private simulated accounts. Launch with python -m riskmatch_v2.studio."""

import argparse
import json
import logging
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import studio_saves as saves
from .matching.ledger import Ledger
from .matching.mandate import MARKET_DAY
from .studio_live import live_value
from .studio_profile import calibrate, deck, intake, money

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
ACCOUNTS = Path(
    os.environ.get("RISKMATCH_STUDIO_ACCOUNTS", ROOT / "data/local/studio/accounts")
)


def public_plan(plan):
    return {k: v for k, v in plan.items() if k != "targets"}


def overview(book, day):
    from .studio_allocation import DAYS

    a = book.account(day)
    if not a["portfolio_version"]:
        return None
    doc = book.export()
    portfolio = doc["portfolios"][-1]
    return {
        "day": day,
        "version": a["portfolio_version"],
        "value": a["value"],
        "cash": a["cash"],
        "positions": len(a["holdings"]),
        "drift": a["drift_max"],
        "history": book.history(),
        "composition": [
            {
                "symbol": s,
                "units": u,
                "value": u * a["prices_chf"][s],
                "weight": a["weights"][s],
            }
            for s, u in sorted(
                a["holdings"].items(), key=lambda item: -a["weights"][item[0]]
            )
        ],
        "live_quote": live_value(a),
        "plan": portfolio["metadata"],
        "parts": portfolio["parts"],
        "next": next((d for d in DAYS if d > day), None),
        "reserve_chf": book.current_mandate()["reserve_chf"],
    }


def _working_mandate(policy, account, day):
    compact = {
        k: account[k]
        for k in (
            "holdings",
            "cash",
            "value",
            "settled_cash",
            "day",
            "prices_chf",
            "stale_symbols",
        )
    }
    if not account["portfolio_version"] and not account["value"]:
        compact.update(
            cash=policy["capital_chf"],
            settled_cash=policy["capital_chf"],
            value=policy["capital_chf"],
        )
    return policy | {"account": compact, "day": day}


def dispatch(action, data, directory=None):
    directory = directory or ACCOUNTS
    if action == "bootstrap":
        return {"day": MARKET_DAY}
    if action == "list_saves":
        return saves.list_saves(directory)
    if action == "create_save":
        return saves.create_save(directory, data)
    if action == "unlock_save":
        return saves.unlock_save(directory, data)
    access = data.get("token")
    if action == "lock_save":
        saves.lock_save(directory, access)
        return {"locked": True}
    token, save_id = saves.resolve(directory, access)
    if action == "intake":
        facts = intake(data["facts"])
        if save_id:
            saves.draft(directory, save_id, facts=data["facts"])
        return facts
    portfolio_check = data.get("portfolio_check") is True
    derived = data.get("derive_volatility") is True
    blocks = derived and data.get("behaviour_blocks") is True
    if action == "route":
        cards, answers = deck(
            data["answers"],
            portfolio_check=portfolio_check,
            derived=derived,
            blocks=blocks,
        )
        if save_id:
            saves.draft(directory, save_id, answers=answers)
        return {"cards": cards, "answers": answers}
    if action == "calibrate":
        facts = intake(data["facts"])
        policy, profile = calibrate(
            facts,
            data["answers"],
            portfolio_check=portfolio_check,
            derived=derived,
            blocks=blocks,
        )
        book = Ledger(directory, token) if token else Ledger.create(directory)
        day = book.latest_day() or MARKET_DAY
        current = book.account(day)
        if token and data.get("version", 0) != current["mandate_version"]:
            raise ValueError(
                "Your profile changed in another session. Reopen it before saving."
            )
        if current["value"] > 0:
            opening = book.current_mandate().get("funded_opening_chf")
            if opening is None:
                opening = next(
                    (
                        r["amount"]
                        for r in book.export()["flows"]
                        if r["event_id"] == "opening"
                    ),
                    None,
                )
            policy["funded_opening_chf"] = opening
            if opening is not None and abs(opening - facts["capital_chf"]) > 0.005:
                policy["blocked_reason"] = profile["blocked_reason"] = (
                    "The funded sleeve differs from this budget. Use a new simulation for a different opening budget."
                )
        if derived:
            from .studio_allocation import apply_preference

            _, profile["volatility_zone"] = apply_preference(
                _working_mandate(policy, current, day)
            )
        policy.update(
            studio_profile=profile,
            studio_intake=data["facts"],
            studio_answers={card["id"]: card["answer"] for card in profile["evidence"]},
        )
        version = book.save_mandate(policy, expected_version=current["mandate_version"])
        return {
            "token": access if save_id else book.token,
            "profile": profile,
            "version": version,
            "funded": bool(current["portfolio_version"]),
        }
    book = Ledger(directory, token)
    latest = book.latest_mandate()
    if action == "resume" and save_id and not latest:
        saved = saves.draft(directory, save_id)
        return {
            "profile": None,
            "version": 0,
            "facts": saved.get("facts", {}),
            "answers": saved.get("answers", {}),
            "funded": False,
        }
    if not latest or not latest["active"]:
        raise ValueError("Reopen a calibrated studio profile.")
    policy = latest["payload"]
    day = book.latest_day() or MARKET_DAY
    if action == "restart_questionnaire":
        if data.get("version") != latest["version"]:
            raise ValueError("The mandate changed. Reopen your latest profile.")
        if save_id:
            saves.draft(
                directory,
                save_id,
                answers={},
                facts=policy["studio_intake"],
                questionnaire_version=latest["version"],
            )
        return {"answers": {}}
    if action == "resume":
        saved = saves.draft(directory, save_id) if save_id else {}
        restarting = saved.get("questionnaire_version") == latest["version"]
        profile = None if restarting else policy["studio_profile"]
        if profile is not None and policy.get("studio_preference") is not None:
            from .studio_allocation import apply_preference

            _, zone = apply_preference(policy | {"day": day})
            profile = profile | {"volatility_zone": zone}
        return {
            "profile": profile,
            "version": latest["version"],
            "facts": saved.get("facts", policy["studio_intake"])
            if restarting
            else policy["studio_intake"],
            "answers": saved.get("answers", {})
            if restarting
            else policy["studio_answers"],
            "funded": bool(book.account(day)["portfolio_version"]),
        }
    if action == "delete":
        if save_id:
            raise ValueError("Protected saves cannot be deleted from the studio.")
        book.delete()
        return {"deleted": True}
    if action == "export":
        return book.export()
    if action == "tracking":
        return overview(book, day)
    if data.get("version") != latest["version"]:
        raise ValueError("The mandate changed. Reopen your latest profile.")
    from .studio_allocation import (
        DAYS,
        STUDIO_RISK_MODEL,
        apply_preference,
        blend,
        candidates,
        compare_goal,
        quotes,
    )

    if action == "advance":
        new_day = next((d for d in DAYS if d > day), None)
        if not new_day or not book.account(day)["portfolio_version"]:
            raise ValueError("No further simulated close is available.")
        if data.get("day") != day:
            return overview(book, day)
        book.mark(new_day, quotes(new_day, book.account(day)["holdings"] or ["SPY"]))
        return overview(book, new_day)
    if action == "flow":
        if data.get("day") != day or not book.account(day)["portfolio_version"]:
            raise ValueError("Refresh the account before recording a cash flow.")
        amount = money(data.get("amount"), "cash flow", minimum=0.01)
        if data.get("direction") not in ("deposit", "withdrawal") or not data.get(
            "event"
        ):
            raise ValueError("Choose a cash-flow direction.")
        book.flow(
            day, amount if data["direction"] == "deposit" else -amount, data["event"]
        )
        return overview(book, day)
    if action == "confirm":
        if policy.get("studio_preference") is not None:
            draft = book.proposal(data["draft"])
            if (
                draft["status"] == "draft"
                and draft["metadata"].get("risk_model") != STUDIO_RISK_MODEL
            ):
                raise ValueError(
                    "This proposal was calculated before the risk update. Calculate your matches again."
                )
        return {
            "version": book.confirm(data["draft"], day),
            "tracking": overview(book, day),
        }
    if action == "cancel":
        book.cancel(data["draft"])
        return {"cancelled": True}
    if action not in ("candidates", "blend", "draft"):
        raise ValueError("Unknown studio action.")
    if policy["blocked_reason"]:
        raise ValueError(policy["blocked_reason"])
    if policy["goal_date"] <= day:
        raise ValueError("Set a future goal date before calculating new matches.")
    a = book.account(day)
    opening = not a["portfolio_version"] and not a["value"]
    working, zone = apply_preference(_working_mandate(policy, a, day))
    if action == "candidates":
        plans = candidates(working)
        return {
            "plans": [public_plan(x) for x in plans],
            "volatility_zone": zone,
            "goal_comparison": compare_goal(working, plans),
            "day": day,
            "revision": a["revision"],
        }
    if data.get("revision") != a["revision"]:
        raise ValueError("The account changed. Calculate your matches again.")
    selected = data.get("ids")
    if (
        not isinstance(selected, list)
        or not selected
        or len(selected) > 10
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("Choose distinct portfolios to combine.")
    weights = data.get("weights")
    plan = blend(working, selected, weights)
    view = public_plan(plan)
    if action == "blend" or not plan["valid"]:
        return {"plan": view, "revision": a["revision"]}
    marks = quotes(day, set(plan["targets"]) | set(a["holdings"]))
    book.mark(day, marks)
    fresh = book.account(day)
    if (
        fresh["holdings"] != a["holdings"]
        or abs(fresh["cash"] - a["cash"]) > 0.001
        or fresh["mandate_version"] != latest["version"]
        or (book.latest_day() or day) != day
    ):
        raise ValueError(
            "The account changed during calculation. Refresh your matches."
        )
    draft = book.propose(
        day,
        plan["targets"],
        plan["parts"],
        metadata=view,
        fund_on_confirmation=opening,
        expected_revision=fresh["revision"],
        expected_mandate=latest["version"],
    )
    return {"plan": view, "draft": draft, "revision": fresh["revision"]}


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/studio":
            self.send_error(404)
            return
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            self.send_error(403)
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("JSON request expected.")
            n = int(self.headers.get("Content-Length", 0))
            if not 1 <= n <= 65536:
                raise ValueError("Request exceeds the demo limit.")
            request = json.loads(self.rfile.read(n))
            result = dispatch(request["action"], request.get("data", {}))
            output = {"ok": True, "result": result}
            status = 200
        except (KeyError, TypeError, ValueError) as exc:
            output = {"ok": False, "error": str(exc)}
            status = 400
        except Exception:
            logging.getLogger(__name__).exception("Studio operation failed")
            output = {
                "ok": False,
                "error": "The simulation could not complete this request.",
            }
            status = 500
        body = json.dumps(output, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=WEB)
    )
    print(f"RiskMatch studio at http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()
