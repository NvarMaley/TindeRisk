"""Read USD quotes for paper portfolios using Alpaca's market-data API."""
import json
import os
import re
from datetime import datetime, timezone
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9./-]{0,14}")
CONFIG = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ALPACA_DATA_FEED")
# Same NYSE common shares under new tickers, confirmed by the issuers.
# BNY: https://www.bny.com/corporate/global/en/about-us/newsroom/press-release/bny-announces-planned-change-of-stock-ticker-symbol-to-bny-130465.html
# Marsh: https://www.marsh.com/en/corp/about/news/marsh-mclennan-to-change-nyse-symbol-to-mrsh.html
TICKER_CHANGES = {"BK": "BNY", "MMC": "MRSH"}


def settings(root):
    local = {}
    path = root / ".env"
    if path.is_file():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in CONFIG:
                local[key.strip()] = value.strip().strip("'\"")
    return {key: os.environ.get(key, local.get(key, "")) for key in CONFIG}


def quotes(root, symbols):
    if (not isinstance(symbols, list) or not 1 <= len(symbols) <= 1000
            or any(not isinstance(s, str) or not SYMBOL.fullmatch(s) for s in symbols)):
        raise ValueError("paperQuotesInvalidSymbols")
    symbols = list(dict.fromkeys(symbols))
    config = settings(root)
    key, secret = config["APCA_API_KEY_ID"], config["APCA_API_SECRET_KEY"]
    feed = config["ALPACA_DATA_FEED"] or "iex"
    if not key or not secret:
        return {"status": "not_configured"}
    if feed not in {"iex", "sip", "delayed_sip"}:
        raise ValueError("paperQuotesInvalidFeed")

    requested = list(dict.fromkeys(TICKER_CHANGES.get(symbol, symbol) for symbol in symbols))
    output = {}
    for offset in range(0, len(requested), 100):
        batch = requested[offset:offset + 100]
        query = urlencode({"symbols": ",".join(batch), "feed": feed})
        request = Request(
            "https://data.alpaca.markets/v2/stocks/trades/latest?" + query,
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
                     "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=7) as response:
                trades = json.load(response)["trades"]
        except HTTPError as exc:
            status = "provider_auth" if exc.code in {401, 403} else "rate_limited" if exc.code == 429 else "provider_unavailable"
            return {"status": status}
        except (URLError, TimeoutError, ValueError, KeyError):
            return {"status": "provider_unavailable"}
        if not isinstance(trades, dict):
            return {"status": "provider_unavailable"}
        for symbol in batch:
            trade = trades.get(symbol)
            if not isinstance(trade, dict):
                continue
            price, stamp = trade.get("p"), trade.get("t")
            try:
                instant = datetime.fromisoformat(stamp)
            except (ValueError, TypeError):
                continue
            if type(price) in (int, float) and isfinite(price) and price > 0 and instant.tzinfo:
                output[symbol] = {"price": price, "as_of": instant.astimezone(timezone.utc).isoformat()}
    quotes_by_holding = {}
    for holding in symbols:
        symbol = TICKER_CHANGES.get(holding, holding)
        if symbol in output:
            quotes_by_holding[holding] = output[symbol]
    return {"status": "ok", "source": "Alpaca", "feed": feed, "quotes": quotes_by_holding,
            "missing": [holding for holding in symbols if holding not in quotes_by_holding]}
