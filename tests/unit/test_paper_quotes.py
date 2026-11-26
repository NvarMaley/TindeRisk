from io import StringIO

import pytest

from riskmatch.market_data import paper_quotes


def test_quotes_only_requests_symbols_and_marks_missing(tmp_path, monkeypatch):
    for key in paper_quotes.CONFIG:
        monkeypatch.delenv(key, raising=False)
    assert paper_quotes.quotes(tmp_path, ["SPY"]) == {"status": "not_configured"}
    (tmp_path / ".env").write_text("APCA_API_KEY_ID=fixture\nAPCA_API_SECRET_KEY=fixture\n")

    def fetch(request, timeout):
        assert request.full_url == "https://data.alpaca.markets/v2/stocks/trades/latest?symbols=SPY%2CIEF&feed=iex"
        assert request.get_header("Apca-api-key-id") == "fixture"
        assert timeout > 0
        return StringIO('{"trades":{"SPY":{"p":123,"t":"2026-11-25T15:00:00Z"}}}')

    monkeypatch.setattr(paper_quotes, "urlopen", fetch)
    result = paper_quotes.quotes(tmp_path, ["SPY", "IEF", "SPY"])
    assert result["quotes"]["SPY"] == {"price": 123, "as_of": "2026-11-25T15:00:00+00:00"}
    assert result["missing"] == ["IEF"]
    with pytest.raises(ValueError, match="paperQuotesInvalidSymbols"):
        paper_quotes.quotes(tmp_path, ["SPY&feed=sip"])


def test_renamed_symbols_keep_the_historical_holding_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "fixture")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "fixture")
    monkeypatch.setenv("ALPACA_DATA_FEED", "sip")

    def fetch(request, timeout):
        assert request.full_url.endswith("symbols=BNY%2CMRSH&feed=sip")
        return StringIO('{"trades":{"BNY":{"p":140,"t":"2026-11-25T15:00:00Z"}}}')

    monkeypatch.setattr(paper_quotes, "urlopen", fetch)
    result = paper_quotes.quotes(tmp_path, ["BK", "BNY", "MMC"])
    assert result["quotes"]["BK"] == result["quotes"]["BNY"]
    assert result["missing"] == ["MMC"]
