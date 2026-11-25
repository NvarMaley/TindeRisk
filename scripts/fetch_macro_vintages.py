"""Collect the Philadelphia Fed's full vintage matrices for four US macroeconomic concepts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import json
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fetch_public_universe_data import ROOT, immutable_save, request

BASE = "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/"
FILES = {
    "real_output": "routputMvQd",
    "unemployment": "rucQvMd",
    "industrial_production": "iptMvMd",
    "consumer_prices": "pcpiMvMd",
}
DEST = ROOT / "data/raw/macro_vintages"


def collect(item):
    series, name = item
    url = BASE + name + ".xlsx"
    data = request(url)
    with ZipFile(BytesIO(data)) as workbook:
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            strings = [
                "".join(v.itertext()) for v in ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            ]
        rows = sheet.findall(".//{*}sheetData/{*}row")
        labels = []
        for cell in rows[0].findall("{*}c"):
            value = cell.findtext("{*}v", "")
            if cell.get("t") == "s":
                value = strings[int(value)]
            if value:
                labels.append(value)
        if len(labels) < 10 or len(rows) < 50:
            raise ValueError("Unexpected vintage matrix dimensions")
    return dict(
        series=series,
        source=url,
        observation_rows=len(rows) - 1,
        vintage_columns=len(labels) - 1,
        first_label=labels[1],
        last_label=labels[-1],
        file=immutable_save(DEST, name, data, "xlsx"),
    )


def main():
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(collect, FILES.items()))
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(acquired_at_utc=datetime.now(timezone.utc).isoformat(), series=results), indent=2
        ).encode(),
        "json",
    )
    print([(r["series"], r["vintage_columns"], r["last_label"]) for r in results])


if __name__ == "__main__":
    main()
