"""Rebuild and verify the 3.1 raw-file inventory without modifying the inputs."""
import argparse
import calendar
import csv
import gzip
import hashlib
import io
import json
import os
import pickletools
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree
from zipfile import ZipFile

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as acsv

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "research/source_catalogue/raw_manifest_v1.csv"
WRDS_DATES = {"crsp_dsf": "DlyCalDt", "crsp_msf": "MthCalDt", "comp_funda": "datadate", "ccm_lnkhist": "LINKDT"}
FIELDS = ("path", "provider", "query_or_source", "retrieved_utc", "vintage", "sha256", "bytes",
          "count_basis", "rows", "first_date", "last_date", "date_field", "missing_codes")


def csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def digest(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def dated_rows(values, basis, field):
    values = list(values)
    return basis, len(values), min(values, default=""), max(values, default=""), field


def projected_csv(source, field):
    # Read logical CSV records including quoted fields. Project one column to bound memory.
    reader = acsv.open_csv(source, read_options=acsv.ReadOptions(block_size=4 << 20),
                           convert_options=acsv.ConvertOptions(include_columns=[field], column_types={field: pa.string()}))
    count, starts, ends = 0, [], []
    for batch in reader:
        count += batch.num_rows
        days = pc.utf8_slice_codeunits(batch.column(0), 0, 10)
        iso = pc.filter(days, pc.match_substring_regex(days, r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"))
        if len(iso):
            limits = pc.min_max(iso).as_py()
            starts.append(limits["min"])
            ends.append(limits["max"])
    return "CSV data records", count, min(starts, default=""), max(ends, default=""), field


def french_file(path):
    with ZipFile(path) as archive:
        lines = archive.read(archive.namelist()[0]).decode("latin1").splitlines()
    if path.stem == "Siccodes12":
        count = sum(bool(re.fullmatch(r"\s*\d{4}-\d{4}\s*", line)) for line in lines)
        return "SIC ranges", count, "", "", ""
    dates = []
    for line in lines:
        key = line.partition(",")[0].strip()
        if re.fullmatch(r"\d{6}|\d{8}", key):
            y, m = int(key[:4]), int(key[4:6])
            day = int(key[6:]) if len(key) == 8 else calendar.monthrange(y, m)[1]
            dates.append(date(y, m, day).isoformat())
    return dated_rows(dates, "factor periods excluding annual summaries", "leading period")


def course_date_column(path):
    """Read the packed datetime column of the two legacy course tables without unpickling."""
    tokens = []
    with path.open("rb") as stream:
        for opcode, arg, _ in pickletools.genops(stream):
            if arg == "_data":
                tokens = ["_data"]
            elif tokens and opcode.name == "BINBYTES":
                if "M8" not in tokens or b"ns" not in tokens or len(arg) % 8:
                    break
                dates = np.frombuffer(arg, dtype="<M8[ns]")
                if len(dates) not in tokens:
                    break
                valid = dates[~np.isnat(dates)].astype("datetime64[D]")
                return "serialized date column", len(dates), str(valid.min()), str(valid.max()), "date UTC"
            elif tokens:
                tokens.append(arg)
    raise ValueError(f"Unrecognised course date encoding in {path}")


def workbook_rows(path):
    # Read the dated BAB worksheet or the year labels of the FOMC sentence corpus.
    days = []
    bab = path.parent.name == "factors"
    with ZipFile(path) as archive:
        strings = []
        if bab:
            shared = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(item.itertext()) for item in shared]
        with archive.open("xl/worksheets/sheet1.xml") as stream:
            for _, row in ElementTree.iterparse(stream, events=("end",)):
                if not row.tag.endswith("}row"):
                    continue
                col = "A" if bab else "B"
                cell = row.find(f"{{*}}c[@r='{col}{row.get('r')}']")
                value = None if cell is None else cell.findtext("{*}v")
                if value and bab and cell.get("t") == "s":
                    value = strings[int(value)]
                    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
                        days.append(datetime.strptime(value, "%m/%d/%Y").date().isoformat())
                elif value and not bab and re.fullmatch(r"\d{4}", value):
                    days.append(value)
                row.clear()
    return dated_rows(days, "BAB factor periods" if bab else "labelled sentences",
                      "first-sheet date" if bab else "year only")


def inventory(root):
    data = root / "data"
    raw = data / "raw"
    public = raw / "public_phase2"
    extra = data / "additional_data"
    downloads = json.loads((data / "processed/metadata.json").read_text())["downloads"]
    fred = json.loads((public / "manifest.json").read_text())
    fred_meta = {r["series"]: r for r in fred["files"]}
    vintages = {f"{r['series']}_{r['vintage']}.csv.gz": r for r in csv_rows(public / "alfred/manifest.csv")}
    vendor = csv_rows(extra / "manifest.csv") + csv_rows(extra / "manifest_diagnosis.csv")
    meta_by_file = {r["source_url_or_query"].split("/")[-1]: r for r in vendor}
    meta_by_id = {r["dataset"]: r for r in vendor}
    paths = sorted(p for folder in (raw, extra / "raw", data / "Data for laboratories-20261119")
                   for p in folder.rglob("*") if p.is_file() and not p.name.startswith(".")
                   and p.name not in ("Icon\r", "manifest.csv", "manifest.json"))
    for path in paths:
        name, key = path.name, path.stem
        with path.open("rb") as stream:
            checksum = digest(stream)
        retrieved, vintage = "unknown", "undocumented export"
        source, provider = name, "course import; original query unavailable"
        missing = "source-specific; not decoded"
        stats = ("opaque supplement; bytes only", "", "", "", "")
        receipt = meta_by_file.get(name) or meta_by_id.get(key)
        if path.parent == extra / "raw/fred":
            receipt = meta_by_id[key.lower()]
        if receipt:
            retrieved, source, provider = (receipt[k] for k in ("downloaded_at_utc", "source_url_or_query", "provider"))
            vintage = "as retrieved"
        if path.parent.name == "alfred":
            v = vintages[name]
            provider, source, vintage = "ALFRED", v["url"], v["vintage"]
            with gzip.open(path, "rb") as stream:
                stats = projected_csv(stream, "observation_date")
            missing = "blank or ."
        elif key in WRDS_DATES:
            stats = projected_csv(str(path), WRDS_DATES[key])
            missing = "blank; field-specific vendor flags; open link end allowed"
        elif key == "etf_prices_adjusted":
            provider, source = "Yahoo Finance via yfinance", "13 tickers; daily auto_adjust=True; see processed/metadata.json"
            retrieved, vintage = downloads["prices"]["downloaded_at_utc"], "current adjustment at retrieval"
            stats = projected_csv(str(path), "date")
            missing = "blank"
        elif path.parent.name == "price_events":
            event = json.loads(path.read_text())
            provider, source, retrieved = "Yahoo Finance chart", event["url"], event["retrieved"]
            vintage = "chart snapshot"
            timestamps = json.loads(event["payload"])["chart"]["result"][0]["timestamp"]
            stats = dated_rows((datetime.fromtimestamp(t, timezone.utc).date().isoformat() for t in timestamps),
                               "daily chart timestamps", "timestamp UTC")
            missing = "JSON null"
        elif key in fred_meta or key in downloads or path.parent.name == "fred":
            if path.parent == public:
                retrieved, source = fred["retrieved_utc"], fred_meta[key]["url"]
            elif path.parent == raw:
                retrieved = downloads[key]["downloaded_at_utc"]
                source = "FRED graph export id=" + key
            provider, vintage, missing = "FRED", "latest at retrieval", "blank or ."
            stats = projected_csv(str(path), "observation_date")
        elif key == "ln7_public_aapl_spy_prices" or name == "sentratio_and_price_st.csv":
            provider = "LN7 local price supplement" if key.startswith("ln7_") else "Course StockTwits aggregate"
            stats = projected_csv(str(path), "date")
            missing = "blank"
        elif key == "statements":
            doc = json.loads(path.read_text())
            provider, source, retrieved = "Federal Reserve", "Historical FOMC archives listed in file", doc["retrieved_at_utc"]
            stats = dated_rows((r["publication_date"] for r in doc["statements"]), "documents", "publication_date")
        elif key == "GICS":
            with ZipFile(path) as archive, archive.open(archive.namelist()[0]) as stream:
                stats = projected_csv(stream, "indfrom")
        elif name == "sector.gz":
            with gzip.open(path, "rb") as stream:
                stats = projected_csv(stream, "datadate")
        elif path.parent.name == "factors" and path.suffix == ".zip":
            stats = french_file(path)
            missing = "consult source header; annual summaries excluded"
        elif path.suffix == ".pkl":
            stats = course_date_column(path)
        elif path.suffix == ".xlsx":
            stats = workbook_rows(path)
            if key.startswith("Betting-"):
                provider = "AQR Capital Management"
        elif key.startswith("q5_factors"):
            rows = csv_rows(path)
            days = (r["date"] if "date" in r else date(int(r["year"]), int(r["month"]), 1).isoformat() for r in rows)
            stats = dated_rows(days, "factor periods", "date or month start")
        yield dict(zip(FIELDS, (path.relative_to(root).as_posix(), provider, source, retrieved, vintage,
                                checksum, path.stat().st_size, *stats, missing), strict=True))


def render(root):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(inventory(root))
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--create", type=Path, help="Write a new version to an unused path")
    mode.add_argument("--verify", type=Path, default=FROZEN, help="Compare against this frozen version")
    args = parser.parse_args()
    current = render(ROOT)
    if args.create:
        with NamedTemporaryFile(mode="w", dir=args.create.parent, newline="", delete=False) as out:
            temporary = Path(out.name)
        try:
            temporary.write_text(current)
            os.link(temporary, args.create)  # Atomic publication; refuse to overwrite an existing version.
        finally:
            temporary.unlink()
    else:
        expected = {r["path"]: r for r in csv_rows(args.verify)}
        observed = {r["path"]: r for r in csv.DictReader(io.StringIO(current))}
        differences = [p for p in sorted(expected.keys() | observed.keys()) if expected.get(p) != observed.get(p)]
        if differences:
            sys.exit("Snapshot rejected. Isolate these inputs from analysis and reconcile against the frozen export:\n" + "\n".join(differences))
    print(f"{len(current.splitlines())-1} raw files {'recorded' if args.create else 'verified'}.")


if __name__ == "__main__":
    main()
