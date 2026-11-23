"""Export only reviewed demo files from this checkout; no network access."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "app/intake.py",
    "app/profile_ui.py",
    "app/swipe/index.html",
    "app/demo_options.py",
    "app/pages/1_Portfolio_options.py",
    "app/pages/2_Portfolio_monitor.py",
    "src/riskmatch/__init__.py",
    "src/riskmatch/intake.py",
    "src/riskmatch/interview.py",
    "src/riskmatch/catalogue.py",
    "src/riskmatch/monitor.py",
    "src/riskmatch/reviews.py",
    "src/riskmatch/demo.py",
    "src/riskmatch/universe.py",
    "data/demo/monitor_feed.json",
    "data/demo/source_events_v1.json",
    "questions/profile_v1.json",
    "research/check_source_fixture.py",
    "requirements-app.txt",
    ".python-version",
]
MAPPING = {f: f for f in FILES}
MAPPING.update(
    {
        f"research/release/demo_catalogue/{name}": f"research/catalogue/{name}"
        for name in ["catalogue.json", "catalogue.sig", "signer.pem"]
    }
)


MAPPING["research/release/demo-requirements.lock"] = "demo-requirements.lock"


MAPPING["research/release/DEMO.md"] = "README.md"


def export(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    expected = json.loads((ROOT / "research/release/public_manifest.json").read_text())
    if set(expected) != set(MAPPING):
        raise ValueError("Unreviewed file list")
    for source, target in MAPPING.items():
        data = (ROOT / source).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected[source]:
            raise ValueError("Unreviewed input " + source)
        out = dest / target
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    return dest


def archive(path):
    with tempfile.TemporaryDirectory() as directory:
        bundle = export(Path(directory) / "demo")
        with ZipFile(path, "w") as output:
            for name in sorted(MAPPING.values()):
                entry = ZipInfo(name, (2026, 11, 23, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                output.writestr(
                    entry, (bundle / name).read_bytes(), compress_type=ZIP_DEFLATED
                )


if __name__ == "__main__":
    if sys.argv[1] == "--zip":
        archive(sys.argv[2])
    else:
        export(sys.argv[1])
