"""Build the full-panel research evidence into a new, atomically published directory."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from riskmatch.universe import ASSETS
from research.universe.comparison import compare
from research.frontier.run import build as frontier
from research.options.run import build as options
from research.execution.run import build as execution


def build(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as tmp:
        stage = Path(tmp) / "results"
        f = stage / "frontier"
        f.mkdir(parents=True)
        frontier(f, ASSETS)
        print("Frontier complete", flush=True)
        o = stage / "options"
        o.mkdir()
        options(o, ASSETS, f)
        print("Client scenarios complete", flush=True)
        execution(stage / "execution", ASSETS, f)
        scores = compare(stage / "execution/cohorts.csv")
        scores.to_csv(stage / "client_value.csv", index=False)
        if destination.exists():
            if (stage / "client_value.csv").read_bytes() != (
                destination / "client_value.csv"
            ).read_bytes():
                raise ValueError("Paired client scores differ")
            for sub in ("frontier", "options", "execution"):
                manifest = json.loads((stage / sub / "manifest.json").read_text())
                if manifest != json.loads(
                    (destination / sub / "manifest.json").read_text()
                ):
                    raise ValueError("Rebuild differs: " + sub)
                for name, expected in manifest.items():
                    existing = destination / sub / name
                    if (
                        existing.exists()
                        and hashlib.sha256(existing.read_bytes()).hexdigest()
                        != expected
                    ):
                        raise ValueError("Corrupt existing result: " + name)
                    if not existing.exists():
                        existing.write_bytes((stage / sub / name).read_bytes())
        else:
            stage.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).parent / "results"
    )
    build(parser.parse_args().output)
