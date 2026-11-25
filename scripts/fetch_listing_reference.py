"""Read public exchange directories and SEC ticker-to-issuer references as dated snapshots."""

from datetime import datetime, timezone
import hashlib
import json

from fetch_public_universe_data import ROOT, immutable_save, request

DEST = ROOT / "data/raw/listing_reference"


def main():
    release = json.loads(
        request("https://api.github.com/repos/iangow/sec_submissions_data/releases/tags/2026-09-30")
    )
    result = {}
    for name in ("tickers.parquet", "former_names.parquet"):
        (row,) = (r for r in release["assets"] if r["name"] == name)
        raw = request(row["browser_download_url"])
        if "sha256:" + hashlib.sha256(raw).hexdigest() != row["digest"]:
            raise ValueError("Incorrect reference checksum")
        result[name] = dict(
            source=row["browser_download_url"],
            file=immutable_save(DEST, name.split(".")[0], raw, "parquet"),
        )
    for name in ("nasdaqlisted", "otherlisted"):
        url = f"https://www.nasdaqtrader.com/dynamic/SymDir/{name}.txt"
        try:
            raw = request(url)
            lines = raw.decode("utf-8-sig").splitlines()
            if "Symbol" not in lines[0] or "File Creation Time" not in lines[-1]:
                raise ValueError("Invalid exchange directory")
            result[name] = dict(
                source=url,
                rows=len(lines) - 2,
                stamp=lines[-1].split("|")[0],
                file=immutable_save(DEST, name, raw, "txt"),
            )
        except (ValueError, OSError) as exc:
            result[name] = dict(source=url, error=type(exc).__name__)
    immutable_save(
        DEST,
        "receipt",
        json.dumps(
            dict(references=result, acquired_at_utc=datetime.now(timezone.utc).isoformat()),
            indent=2,
        ).encode(),
        "json",
    )
    print({k: v.get("rows", v.get("error", "verified")) for k, v in result.items()})


if __name__ == "__main__":
    main()
