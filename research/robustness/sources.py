"""Extract the required research series from official Fed and French downloads."""

import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
NAMES = {
    "value": "6_Portfolios_2x3",
    "profitability": "6_Portfolios_ME_OP_2x3",
    "investment": "6_Portfolios_ME_INV_2x3",
    "momentum": "6_Portfolios_ME_Prior_12_2",
}
URLS = {
    "curve": "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv",
    **{
        name: "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        + name
        + "_CSV.zip"
        for name in NAMES.values()
    },
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def extract(blobs, out, retrieval_date):
    rows = []
    for signal, name in NAMES.items():
        with zipfile.ZipFile(io.BytesIO(blobs[name])) as z:
            lines = z.read(z.namelist()[0]).decode("latin1").splitlines()
        start = next(
            i
            for i, line in enumerate(lines)
            if line.strip() == "Average Value Weighted Returns -- Monthly"
        )
        header = lines[start + 1].split(",")[1:]
        if (
            len(header) != 6
            or "SMALL" not in header[0].upper()
            or "BIG" not in header[3].upper()
        ):
            raise ValueError("Unexpected portfolio headings")
        for line in lines[start + 2 :]:
            if not re.match(r"^\s*\d{6},", line):
                break
            date, *cells = line.strip().split(",")
            if not "201401" <= date <= "202512":
                continue
            for size, idx in [("small", 0), ("big", 3)]:
                favored = idx + (0 if signal == "investment" else 2)
                a, b = float(cells[favored]), float(cells[idx + 1])
                if min(a, b) <= -99:
                    raise ValueError("Missing portfolio return")
                rows.append((date[:4] + "-" + date[4:], signal, size, a / 100, b / 100))
    french = pd.DataFrame(
        rows, columns=["month", "signal", "size", "favorable", "middle"]
    )
    if len(french) != 144 * 8 or french.duplicated(["month", "signal", "size"]).any():
        raise ValueError("Incomplete French panel")
    french.to_csv(out / "french_portfolios.csv", index=False)
    raw = blobs["curve"].decode("utf-8-sig")
    curve = pd.read_csv(
        io.StringIO(raw[raw.index("Date,BETA0") :]),
        usecols=["Date", *[f"SVENY{i:02}" for i in range(1, 6)]],
    )
    curve = (
        curve[curve.Date.between("2004-12-01", "2026-10-30")]
        .dropna()
        .sort_values("Date")
    )
    if curve.Date.duplicated().any():
        raise ValueError("Duplicate curve dates")
    curve.to_csv(out / "zero_yields.csv", index=False)
    manifest = {
        "retrieval_date": retrieval_date,
        "downloads": {k: {"url": v, "sha256": sha(blobs[k])} for k, v in URLS.items()},
        "extracts": {
            n: sha((out / n).read_bytes())
            for n in ["zero_yields.csv", "french_portfolios.csv"]
        },
    }
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    blobs = {}
    for k, u in URLS.items():
        if args.cache:
            blobs[k] = (args.cache / k).read_bytes()
        else:
            req = urllib.request.Request(
                u,
                headers={
                    "User-Agent": "RiskMatch academic research, NvarMaley/TindeRisk (github.com/NvarMaley/TindeRisk)"
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                blobs[k] = response.read()
    retrieved = datetime.now(UTC).date().isoformat()
    if args.cache:
        frozen = json.loads((HERE / "inputs/provenance.json").read_text())
        if any(
            sha(blob) != frozen["downloads"][name]["sha256"]
            for name, blob in blobs.items()
        ):
            raise ValueError("Cached inputs differ from the documented retrieval")
        retrieved = frozen["retrieval_date"]
    manifest = extract(blobs, args.output, retrieved)
    (args.output / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
