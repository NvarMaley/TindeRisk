"""Check the distributed bytes against the reviewed allowlist and demo scope."""

from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from zipfile import ZipFile

from package import ROOT, MAPPING, archive


def verify():
    release = ROOT / "research/release"
    source = release / "RiskMatch-demo.zip"
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "demo.zip"
        archive(rebuilt)
        assert source.read_bytes() == rebuilt.read_bytes(), (
            "Archive differs from clean build"
        )
    manifest = json.loads((release / "public_manifest.json").read_text())
    forbidden = re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}"
    )
    with ZipFile(source) as bundle:
        assert sorted(bundle.namelist()) == sorted(MAPPING.values())
        for original, dest in MAPPING.items():
            content = bundle.read(dest)
            assert hashlib.sha256(content).hexdigest() == manifest[original]
            assert not forbidden.search(content), dest
            assert not dest.endswith((".sqlite3", ".parquet", ".env"))
        assert {n for n in bundle.namelist() if n.startswith("data/")} == {
            "data/demo/monitor_feed.json",
            "data/demo/source_events_v1.json",
        }
        with tempfile.TemporaryDirectory() as tmp:
            bundle.extractall(tmp)
            sys.path.insert(0, str(Path(tmp) / "src"))
            from riskmatch.catalogue import approved

            assert approved(
                "demo/manual/v1",
                date(2026, 11, 23),
                "CHF",
                "illustrative CHF 50000",
                "synthetic local demonstration",
                Path(tmp) / "research/catalogue",
            )
    print(
        f"{len(MAPPING)} reviewed files, identical rebuild, synthetic data and catalogue signature verified."
    )
    print(hashlib.sha256(source.read_bytes()).hexdigest())


if __name__ == "__main__":
    verify()
