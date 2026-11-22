"""Run the fictional 3.1 ledger with only the standard library."""
import json
from decimal import Decimal
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "data/demo/source_events_v1.json"


def replay(fixture, sessions):
    units = Decimal(fixture["opening_units"])
    cash = Decimal(fixture["opening_cash_chf"])
    releases = sorted(fixture["vintages"], key=lambda r: r["available"])
    rows = []
    for session in sessions:
        day = session["date"]
        if rows and day <= rows[-1][0]:
            raise ValueError("Sessions must be unique and ordered")
        units *= Decimal(session.get("split", "1"))
        if "delist_cash_usd" in session:
            cash += units * Decimal(session["delist_cash_usd"]) * Decimal(session["chf_per_usd"])
            units = Decimal(0)
        cash -= Decimal(session.get("withdraw_chf", "0"))
        if cash < 0:
            raise ValueError("Insufficient settled CHF")
        wealth = None if units else cash
        if units and session.get("close_usd") is not None:
            wealth = cash + units * Decimal(session["close_usd"]) * Decimal(session["chf_per_usd"])
        known = [r["value"] for r in releases if r["available"] < day]
        rows.append([day, str(units), f"{cash:.2f}", None if wealth is None else f"{wealth:.2f}",
                     known[-1] if known else None])
    return rows


def check():
    fixture = json.loads(FIXTURE.read_text())
    if fixture["synthetic"] is not True:
        raise ValueError("Fictional fixture required")
    sessions = fixture["sessions"]
    actual = replay(fixture, sessions)
    if actual != fixture["expected_rows"]:
        raise AssertionError((actual, fixture["expected_rows"]))
    bad = fixture["rejected_case"]
    changed = [dict(s, withdraw_chf=bad["withdraw_chf"]) if s["date"] == bad["date"] else s for s in sessions]
    try:
        replay(fixture, changed)
    except ValueError as error:
        if str(error) != bad["expected_error"]:
            raise
    else:
        raise AssertionError("Expected the unfunded withdrawal to fail")
    return actual


if __name__ == "__main__":
    print(f"Synthetic only. {len(check())} ledger rows match. Unfunded withdrawal rejected.")
