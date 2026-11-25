"""Translate verified local matrix/archive receipts into typed research inputs."""
import calendar
import csv
from datetime import date, datetime
import json
import gzip
from math import isfinite
import re
from xml.etree import ElementTree
from zipfile import ZipFile


def factor_rows(path, source_hash):
    daily = "_daily-" in path.name
    with ZipFile(path) as archive:
        lines = archive.read(archive.namelist()[0]).decode("utf-8-sig").splitlines()
    fields = None
    for row in csv.reader(lines):
        if not row:
            continue
        first = row[0].strip()
        if not first and len(row) > 1:
            fields = [value.strip() for value in row[1:]]
        if fields is None or not re.fullmatch(r"\d{8}" if daily else r"\d{6}", first):
            continue
        day = datetime.strptime(first, "%Y%m%d" if daily else "%Y%m").date()
        if not daily:
            day = day.replace(day=calendar.monthrange(day.year, day.month)[1])
        for factor, value in zip(fields, row[1:], strict=True):
            number = float(value)
            if isfinite(number) and number not in (-99.99, -999):
                yield factor, day, "daily" if daily else "monthly", number / 100, source_hash


def column_index(ref):
    result = 0
    for char in ref:
        if not char.isalpha():
            break
        result = result * 26 + ord(char.upper()) - ord("A") + 1
    return result


def macro_rows(path, series, source_hash):
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.itertext()) for node in ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))]
        with archive.open("xl/worksheets/sheet1.xml") as sheet:
            labels = None
            for _, row in ElementTree.iterparse(sheet, events=("end",)):
                if not row.tag.endswith("}row"):
                    continue
                cells = {}
                for cell in row.findall("{*}c"):
                    item = cell.findtext("{*}v", "")
                    if cell.get("t") == "s" and item:
                        item = strings[int(item)]
                    cells[column_index(cell.get("r", ""))] = item
                if labels is None:
                    labels = cells
                else:
                    match = re.fullmatch(r"(\d{4}):(?:Q)?(\d{1,2})", cells.get(1, ""))
                    if match:
                        year, period = map(int, match.groups())
                        month = (period-1)*3+1 if series == "real_output" else period
                        day = date(year, month, 1)
                        for index, item in cells.items():
                            if index == 1 or not item or index not in labels:
                                continue
                            try:
                                value = float(item)
                            except ValueError:
                                continue
                            if isfinite(value):
                                yield series, day, labels[index], value, source_hash
                row.clear()


def supplemental_inputs(data, stage, verified, digest):
    root = data/"raw"
    factor_files = sorted((root/"public_universe").rglob("F-F_*.zip"))
    factor_path = stage/"factor_input.csv"
    with factor_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","frequency","value","original_source_hash"))
        for path in factor_files:
            sha = digest(path)
            writer.writerows(factor_rows(path, sha))
    yield ("fama_french",factor_path,"*", "instrument,observation_date,frequency", "isfinite(value)", "decimal per period")
    folder = root/"macro_vintages"
    receipt = json.loads(next(folder.glob("receipt-*.json")).read_text())
    macro_path = stage/"macro_input.csv"
    with macro_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","vintage_label","value","original_source_hash"))
        for entry in receipt["series"]:
            source = verified(folder, entry["file"])
            writer.writerows(macro_rows(source, entry["series"], entry["file"]["sha256"]))
    yield ("macro_vintages",macro_path,"*", "instrument,observation_date,vintage_label", "isfinite(value)", "source-specific units; vintage label")
    marks_path = stage/"fedinvest_input.csv"
    with marks_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","class","maturity_date","buy_mark","sell_mark","eod_price","original_source_hash"))
        for file in sorted((root/"fedinvest").glob("*/receipt-*.json")):
            receipt = json.loads(file.read_text())
            source = verified(file.parent, receipt["file"])
            with source.open() as rows:
                for row in csv.DictReader(rows):
                    if row["SECURITY TYPE"] not in {"MARKET BASED BILL","MARKET BASED NOTE","MARKET BASED BOND","TIPS"}:
                        continue
                    if row["date"] != receipt["date"]:
                        raise ValueError("FedInvest date mismatch")
                    writer.writerow((row["CUSIP"],row["date"],row["SECURITY TYPE"],row["MATURITY DATE"],row["BUY"],row["SELL"],row["END OF DAY"],receipt["file"]["sha256"]))
    yield ("fedinvest_marks",marks_path,"*", "instrument,observation_date", "eod_price>0 and isfinite(eod_price)", "USD per 100 face; government valuation")
    folder = root/"issuer_assets"
    receipt = json.loads(next(folder.glob("receipt-*.json")).read_text())
    assets_path = stage/"assets_input.csv"
    with assets_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","net_assets_usd","original_source_hash"))
        for entry in receipt["funds"]:
            verified(folder, entry["file"])
            writer.writerow((entry["ticker"],entry["as_of"],entry["net_assets_usd"],entry["file"]["sha256"]))
    yield ("issuer_assets",assets_path,"*", "instrument,observation_date", "net_assets_usd>0", "USD")
    folder = root/"tips_ratios"
    receipt_path = next(folder.glob("*/receipt-*.json"))
    receipt = json.loads(receipt_path.read_text())
    ratio_path = stage/"tips_ratio_input.csv"
    with ratio_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","index_ratio","reference_cpi","reported_updated_timestamp","original_source_hash"))
        for entry in receipt["issues"]:
            if "file" not in entry:
                continue
            source = verified(receipt_path.parent, entry["file"])
            with gzip.open(source,"rt") as rows:
                for row in json.load(rows):
                    if row["cusip"] != entry["cusip"] or row["indexType"] != "CPI" or not row.get("indexRatio"):
                        continue
                    writer.writerow((row["cusip"],row["indexDate"][:10],row["indexRatio"],row.get("referenceCPI"),row.get("updatedTimestamp"),entry["file"]["sha256"]))
    yield ("tips_daily_index_ratios",ratio_path,"*", "instrument,observation_date", "index_ratio>0", "indexation ratio; source update time as reported")
    identity_source = data/"processed/universe/treasury_identity.json"
    identity = json.loads(identity_source.read_text())
    identity_path = stage/"treasury_identity_input.csv"
    with identity_path.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("instrument","observation_date","instrument_type","currency","issue_date","maturity","coupon_rate_decimal","original_source_hash"))
        sha = digest(identity_source)
        for row in identity["rows"]:
            writer.writerow((row["cusip"],row["first_observed_record_date"],row["instrument_type"],row["currency"],
                             row["first_observed_issue_date"],row["maturity"],row["coupon_rate_decimal"],sha))
    yield ("treasury_identity",identity_path,"*", "instrument,observation_date", "currency='USD' and maturity>=issue_date", "dated sovereign identity; decimal coupon")
