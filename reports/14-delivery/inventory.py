"""Inventory the tracked release. Raw market files and saved accounts stay outside Git."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = "reports/14-delivery/public-files.json"
PREDICTIONS = {
    f"reports/12-forecasts/{name}-predictions.csv"
    for name in ("return-21", "variance-21", "variance-63")
}


def classification(name):
    p = Path(name)
    if (
        p.parts[:2] == ("data", "local")
        or any(part.startswith(".env") for part in p.parts)
        or p.suffix
        in {".sqlite3", ".db", ".parquet", ".npz", ".pem", ".key", ".xlsx", ".zip"}
    ):
        raise ValueError(f"Private archive or local state in release: {name}")
    if name == "src/riskmatch_v2/demo/returns.csv":
        return "synthetic fixture"
    if name in PREDICTIONS:
        return "paired derived predictions and outcomes"
    if p.suffix == ".csv":
        raise ValueError(f"Review new tabular data before release: {name}")
    if name.startswith("reports/07-funding/client-") or name.endswith("/cas.json"):
        return "fictional research cases"
    if name in {"web/assets/lagoon-jazz.m4a", "web/assets/lagoon-cues.m4a"}:
        return "original studio music and sound effects"
    if p.suffix == ".woff2" or name.endswith("OFL.txt"):
        return "font and bundled licence"
    if p.suffix in {".webp", ".jpg", ".png"}:
        return "research chart, fictional screenshot or project artwork"
    if p.suffix in {".md", ".ipynb"}:
        return "documentation and notebooks"
    if p.suffix == ".json":
        return "parameters, metadata and research evidence"
    if (
        p.suffix in {".py", ".js", ".css", ".html", ".sql", ".toml", ".txt"}
        or name == ".gitignore"
    ):
        return "software, configuration and environment"
    raise ValueError(f"Unclassified file: {name}")


def inventory():
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    files = {name: classification(name) for name in names if name}
    inputs = [
        "reports/univers-complet/resultats.json",
        "reports/13-application/market.json",
        "reports/13-application/market-replay.json",
        "reports/14-delivery/intraday.json",
        "reports/07-funding/client-A.json",
        "reports/07-funding/client-B.json",
        "reports/14-delivery/requirements-macos-arm64-py312.txt",
    ]
    return {
        "tracked_count": len(files),
        "files": files,
        "input_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in inputs
        },
    }


if __name__ == "__main__":
    import sys

    result = inventory()
    if "--write" in sys.argv:
        (ROOT / OUTPUT).write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads((ROOT / OUTPUT).read_text()), (
            "Release manifest differs"
        )
    print(
        f"{result['tracked_count']} tracked files classified; {len(result['input_sha256'])} inputs fingerprinted."
    )
