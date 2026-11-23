"""Read an optional operator-authorised USD-equity and USD/CHF quote feed for display."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd


def live_value(account, *, path=None, now=None):
    now = now or datetime.now(UTC)
    path = path or os.environ.get("RISKMATCH_LIVE_MARKS")
    fallback = {"live": False, "observed_at": now.isoformat()}
    if not path:
        return fallback | {"reason": "No authorised live feed is connected."}
    try:
        from math import isfinite

        payload = json.loads(Path(path).read_text())
        if (
            payload["mode"] != "realtime"
            or payload["display_authorized"] is not True
            or not payload["source"].strip()
        ):
            raise ValueError("The feed does not declare real-time display permission.")
        if not xcals.get_calendar("XNYS").is_open_on_minute(
            pd.Timestamp(now).floor("min")
        ):
            raise ValueError("The US regular trading session is closed.")
        if not account["holdings"]:
            raise ValueError("The account has no securities to mark.")

        def checked(row):
            stamp = datetime.fromisoformat(row["at"])
            if stamp.tzinfo is None or not 0 <= (now - stamp).total_seconds() <= 90:
                raise ValueError("A security or FX quote is stale or future-dated.")
            price = float(row["value"])
            if not isfinite(price) or price <= 0:
                raise ValueError("A required quote is invalid.")
            return stamp, price

        fx_time, fx = checked(payload["usd_chf"])
        stamps = [fx_time]
        value = account["cash"]
        for symbol, units in account["holdings"].items():
            mark = payload["securities"][symbol]
            if mark["currency"] != "USD" or mark.get("unit") != "ledger_unit":
                raise ValueError(
                    "Quote currency or unit differs from the held position."
                )
            stamp, price = checked(mark)
            stamps.append(stamp)
            value += units * price * fx
        return {
            "live": True,
            "source": payload["source"],
            "value": value,
            "oldest_at": min(stamps).astimezone(UTC).isoformat(),
            "observed_at": now.isoformat(),
        }
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
    ) as exc:
        reason = (
            str(exc)
            if isinstance(exc, ValueError) and type(exc) is ValueError
            else "The feed is unavailable or incomplete."
        )
        return fallback | {"reason": reason}
