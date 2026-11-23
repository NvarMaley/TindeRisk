"""Dated external releases, immutable GPR editions and conservative alignment."""

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW = Path("data/local/12/raw")
REPORT = Path("reports/12-forecasts")
CONFIG = Path("config/forecasts-12.json")
FED = "https://www.federalreserve.gov"
TREE = "5996a1a1b5913cfe24ce312cc3ba032288c6722e"
HAWK = {
    "inflation",
    "inflationary",
    "elevated",
    "tightening",
    "tighten",
    "restrictive",
    "overheating",
}
DOVE = {
    "weakness",
    "weak",
    "easing",
    "accommodation",
    "accommodative",
    "unemployment",
    "slowing",
    "downturn",
}


def fetch(name, url):
    dest = RAW / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with requests.Session() as session:
            session.mount(
                "https://",
                HTTPAdapter(
                    max_retries=Retry(
                        total=3,
                        backoff_factor=0.5,
                        status_forcelist=[429, 502, 503, 504],
                    )
                ),
            )
            r = session.get(url, timeout=45)
            r.raise_for_status()
            temp = dest.with_suffix(".download")
            temp.write_bytes(r.content)
            temp.replace(dest)
    return dest


def statement(url):
    day = re.search(r"(\d{8})[a-z]?\.htm", url)[1]
    soup = BeautifulSoup(
        fetch("fed/" + day + "-" + url.rsplit("/", 1)[-1], url).read_bytes(),
        "html.parser",
    )
    body = soup.select_one("#article .col-xs-12.col-sm-8.col-md-8:not(.heading)")
    if body is None:
        return None
    paragraphs = [p.get_text(" ", strip=True) for p in body.select("p")]
    content = " ".join(
        s
        for s in paragraphs
        if s and not s.startswith(("Voting", "For media", "Last Update"))
    )
    if len(content) < 180 or "committee" not in content.lower():
        return None
    words = re.findall(r"[a-z]+", content.lower())
    score = (
        100
        * (sum(t in HAWK for t in words) - sum(t in DOVE for t in words))
        / len(words)
    )
    # Uniform conservative upper bound when an intraday publication clock is absent.
    end = pd.Timestamp(day).tz_localize("America/New_York") + pd.Timedelta(
        hours=23, minutes=59
    )
    sha = hashlib.sha256(content.encode()).hexdigest()
    (RAW / "fed" / (sha + ".txt")).write_text(content)
    return {
        "url": url,
        "published_day": str(end.date()),
        "available": end.tz_convert("UTC").isoformat(),
        "sha256_text": sha,
        "tone": score,
        "words": len(words),
    }


def collect():
    manifest = REPORT / "fomc-releases.json"
    urls = (
        {r["url"] for r in json.loads(manifest.read_text())}
        if manifest.exists()
        else set()
    )
    locked = bool(urls)
    for year in range(2006, 2027):
        page = f"fomchistorical{year}.htm" if year < 2021 else "fomccalendars.htm"
        # The last five years share the same live calendar.
        if locked or year > 2021:
            break
        src = fetch(page, FED + "/monetarypolicy/" + page)
        for a in BeautifulSoup(src.read_bytes(), "html.parser").select("a[href]"):
            href = a["href"]
            if a.get_text(strip=True) in ("Statement", "HTML") and re.search(
                r"monetary/?\d{8}[a-z]\.htm$", href
            ):
                date = re.search(r"(\d{8})[a-z]\.htm", href)[1]
                # Modern calendar also links minutes and other HTML. Require statement context.
                if a.get_text(
                    strip=True
                ) == "HTML" and "Statement:" not in a.parent.get_text(" ", strip=True):
                    continue
                if date <= "20261030":
                    urls.add(urljoin(FED, href))
    with ThreadPoolExecutor(4) as pool:
        releases = [x for x in pool.map(statement, sorted(urls)) if x]
    releases = (
        pd.DataFrame(releases)
        .sort_values(["available", "url"])
        .drop_duplicates("sha256_text")
    )
    records = releases[
        ["url", "published_day", "available", "sha256_text", "words", "tone"]
    ].to_dict("records")
    if locked and json.loads(manifest.read_text()) != records:
        raise ValueError("FOMC release content differs from the published corpus")
    if not locked:
        manifest.write_text(json.dumps(records, indent=2) + "\n")
    releases.to_parquet(RAW / "statements.parquet", index=False)
    tree = json.loads(
        fetch(
            "gpr-tree.json",
            f"https://api.github.com/repos/iacoviel/iacoviel.github.io/git/trees/{TREE}?recursive=1",
        ).read_bytes()
    )
    files = [
        x["path"]
        for x in tree["tree"]
        if re.fullmatch(r"gpr_archive_files/data_gpr_export_\d{6}\.dta", x["path"])
        and x["path"][-10:-4] <= "202610"
    ]

    def gpr(path):
        name = path.rsplit("/", 1)[1]
        vintage = pd.Period(name[-10:-4], freq="M")
        data = pd.read_stata(
            fetch(
                "gpr/" + name,
                f"https://raw.githubusercontent.com/iacoviel/iacoviel.github.io/{TREE}/{path}",
            ),
            convert_categoricals=False,
        )
        data.columns = data.columns.str.lower()
        prior = (
            data[data.month < vintage.start_time]
            .dropna(subset=["gpr"])
            .sort_values("month")
        )
        last = prior.iloc[-1]
        return {
            "vintage": str(vintage),
            "observation": str(last.month.date()),
            "available": vintage.end_time.date().isoformat(),
            "gpr": float(last.gpr),
        }

    with ThreadPoolExecutor(4) as pool:
        editions = pd.DataFrame(pool.map(gpr, sorted(files)))
    editions.to_parquet(RAW / "gpr.parquet", index=False)
    fetch(
        "vix.csv",
        "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
    )
    print(
        "Distinct statements",
        len(releases),
        releases.published_day.min(),
        releases.published_day.max(),
        "GPR editions",
        len(editions),
    )


def vintage_unemployment():
    hist = (
        pd.read_parquet("data/local/4/raw/macro_releases.parquet")
        .query("series == 'UNRATE'")
        .sort_values(["available_at", "observation_date"])
    )
    return hist.groupby("available_at").tail(1).set_index("available_at").value, hist


def asof(series, dates, max_age):
    series = series.dropna().sort_index()
    times = pd.to_datetime(series.index, utc=True)
    q = pd.to_datetime(dates, utc=True)
    if not len(times):
        return np.full(len(q), np.nan)
    i = times.searchsorted(q, side="left") - 1
    pos = np.maximum(i, 0)
    value = series.to_numpy()[pos].astype(float)
    value[(i < 0) | ((q - times[pos]) > pd.Timedelta(days=max_age))] = np.nan
    return value


def frame():
    cat = Path("data/local/4/4.0-2026-11-23")
    prices = pd.read_parquet(cat / "prices.parquet")
    prices["symbol"] = prices.id.str.split("-").str[-1]
    fund = (
        prices.query("symbol=='SPY'")
        .set_index("day")
        .sort_index()
        .loc[:"2026-10-30"]
        .dropna(subset=["adjusted", "fx"])
        .copy()
    )
    fund.index = pd.to_datetime(fund.index)
    price = fund.adjusted * fund.fx
    r = price.pct_change(fill_method=None)
    f = pd.DataFrame(index=price.index)
    f["realized"] = np.log(r.pow(2).rolling(21).mean())
    f["momentum"] = price.shift(21) / price.shift(126) - 1
    dollar = fund.close * fund.volume
    f["liquidity"] = np.log(dollar.rolling(5).mean() / dollar.rolling(63).mean())
    vix = pd.read_csv(RAW / "vix.csv", parse_dates=["DATE"]).set_index("DATE").CLOSE
    f["vix"] = asof(vix, f.index + pd.Timedelta(hours=23), 5)

    def rate(file, key):
        return pd.read_csv(file, parse_dates=["observation_date"]).set_index(
            "observation_date"
        )[key]

    curve = (
        rate("data/local/4/raw/DGS10.csv", "DGS10")
        - rate("data/local/8/DGS2.csv", "DGS2")
    ).dropna()
    curve.index += pd.offsets.BDay(2)
    f["curve"] = asof(curve, f.index, 10)
    un, history = vintage_unemployment()
    f["unemployment"] = asof(un, f.index + pd.Timedelta(hours=23), 65)
    text = pd.read_parquet(RAW / "statements.parquet")
    f["tone"] = asof(
        text.set_index("available").tone, f.index + pd.Timedelta(hours=23), 100
    )
    geo = pd.read_parquet(RAW / "gpr.parquet")
    f["gpr"] = asof(geo.set_index("available").gpr, f.index, 65)
    # Every predictor, including a published index, stops at the preceding session.
    return (
        r,
        f.shift(1),
        prices,
        {
            "statements": len(text),
            "gpr_editions": len(geo),
            "tone_start": text.published_day.min(),
            "tone_end": text.published_day.max(),
            "gpr_start": geo.available.min(),
            "gpr_end": geo.available.max(),
            "training_statements": int((text.published_day < "2015").sum()),
            "macro_vintages": int(history.vintage.nunique()),
            "revised_observations": int(
                (history.groupby("observation_date").value.nunique() > 1).sum()
            ),
        },
    )


if __name__ == "__main__":
    collect()
