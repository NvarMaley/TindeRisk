"""Liquidity observations and value-date controls for the research mandate."""

import gzip
from decimal import ROUND_HALF_UP, Decimal
from xml.etree import ElementTree

import pandas as pd

from ..universe.treasury import RAW
from .pricing import discounted, remaining, schedule


def marks(day):
    root = ElementTree.fromstring(
        gzip.decompress((RAW / (day + ".xml.gz")).read_bytes())
    )
    rows = [{el.tag: el.text for el in item} for item in root.iter("Security")]
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows).set_index("Cusip")
    if not d.PriceDate.eq(day).all() or not d.index.is_unique:
        raise ValueError("Unexpected security or price date")
    for k in ("EODPrice", "BuyPrice", "SellPrice", "Rate"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    return d


def dollars(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def auction_gate(face, minimum, increment, cost, cash, due, access):
    if face < minimum or face % increment:
        return "Invalid lot"
    if not access:
        return "Unverified account"
    settled = sum(value for day, value in cash if day <= due)
    return (
        "Funded on settlement date" if settled >= cost else "Insufficient settled USD"
    )


def replay(cfg, auctions, terms, history, notes):
    key = cfg["example"]
    a = auctions[
        (auctions.cusip == key) & (auctions.auction_date == cfg["auction_date"])
    ].iloc[0]
    t = terms.loc[key]
    flows = schedule(t.dated_date, t.maturity_date, t.int_rate)
    after, fraction, ai = remaining(flows, a.issue_date)
    pv = discounted(
        (after.coupon + after.principal).to_numpy(), fraction, float(a.high_yield) / 100
    )[0]
    clean = pv - ai
    assert (
        abs(clean - float(a.price_per100)) < 1e-6
        and abs(10 * ai - float(a.accrued_int_per1000)) < 1e-5
    )
    face = cfg["face_usd"]
    charge = dollars(
        (float(a.price_per100) + float(a.accrued_int_per1000) / 10) * face / 100
    )
    due = a.issue_date
    minimum, inc = int(a.min_bid_amt), int(a.multiples_to_bid)
    after_due = str((pd.Timestamp(due) + pd.Timedelta(days=1)).date())
    tests = {}
    for title, order, cash, access in [
        ("Funded auction example", face, [(due, 1000)], True),
        ("Odd lot", face + 50, [(due, 2000)], True),
        ("Cash after settlement", face, [(after_due, 1000)], True),
        ("Client account", face, [(due, 1000)], False),
    ]:
        tests[title] = auction_gate(
            order, minimum, inc, dollars(charge * order / face), cash, due, access
        )
    assert len(set(tests.values())) == 4
    first = after.iloc[0]
    coupon_cash = dollars(first.coupon * face / 100)
    entry = history[
        (history.name == "UST:" + key) & history.day.eq(str(first.pay.date()))
    ].iloc[0]
    prev = history[
        (history.name == entry["name"]) & history.day.eq(entry.previous)
    ].iloc[0]
    assert (
        abs(entry.income - first.coupon) < 1e-8
        and abs((entry.close + entry.income) / prev.close - 1 - entry.usd) < 1e-10
    )
    # Independent matured note, outside the 65 selected. Verify its final mark,
    # contractual principal and coupon, and removal of the mark on maturity.
    ctl = notes[0]
    mat = schedule(ctl["datedDate"][:10], ctl["maturityDate"][:10], ctl["interestRate"])
    final = mat.iloc[-1]
    last = str((final.due - pd.Timedelta(days=1)).date())
    mark = marks(last).loc[cfg["matured_control"]]
    assert (
        float(ctl["interestRate"]) == mark.Rate * 100
        and pd.Timestamp(mark.MaturityDate) == final.due
    )
    maturity_marks = marks(str(final.due.date()))
    matured_quote = (
        None
        if cfg["matured_control"] not in maturity_marks.index
        else float(maturity_marks.loc[cfg["matured_control"], "EODPrice"])
    )
    redemption = dollars((final.coupon + final.principal) * face / 100)
    remaining_face = face - final.principal * face / 100
    assert remaining_face == 0 and matured_quote is None
    ledger = [
        {
            "cusip": key,
            "day": due,
            "event": "Funded purchase settlement",
            "change_usd": -charge,
            "balance_usd": dollars(1000 - charge),
            "remaining_face": face,
        },
        {
            "cusip": key,
            "day": str(first.pay.date()),
            "event": "First coupon after purchase",
            "change_usd": coupon_cash,
            "balance_usd": dollars(1000 - charge + coupon_cash),
            "remaining_face": face,
        },
        {
            "cusip": cfg["matured_control"],
            "day": str(final.pay.date()),
            "event": "Separate maturity control, zero opening cash",
            "change_usd": redemption,
            "balance_usd": redemption,
            "remaining_face": remaining_face,
        },
    ]
    return {
        "cash_ledger": ledger,
        "example": key,
        "auction": a.auction_date,
        "issue_settlement": due,
        "noncompetitive_accepted_usd": int(a.noncomp_accepted),
        "minimum_face": minimum,
        "increment": inc,
        "face": face,
        "auction_yield": float(a.high_yield) / 100,
        "previous_coupon": str(first.start.date()),
        "next_coupon": str(first.due.date()),
        "fraction_left": fraction,
        "coupon_per100": first.coupon,
        "accrued_per100": ai,
        "clean_official": float(a.price_per100),
        "clean_calculated": clean,
        "dirty_per100": pv,
        "settlement_debit": charge,
        "cash_after_purchase": dollars(1000 - charge),
        "cash_after_coupon": dollars(1000 - charge + coupon_cash),
        "coupon_date": str(first.pay.date()),
        "coupon_usd": coupon_cash,
        "coupon_day_total_return": entry.usd,
        "gate_tests": tests,
        "matured_control": {
            "cusip": cfg["matured_control"],
            "last_mark_day": last,
            "last_clean": float(mark.EODPrice),
            "pay": str(final.pay.date()),
            "face": face,
            "coupon_unrounded": final.coupon * face / 100,
            "principal": final.principal * face / 100,
            "projected_cash_rounded": dollars(
                (final.coupon + final.principal) * face / 100
            ),
            "maturity_mark": matured_quote,
        },
    }
