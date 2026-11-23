"""Rebuild the dated simulation and scan the tracked release for private test markers."""

import json
import subprocess
from pathlib import Path

from .engine import Market, engine_replay
from .ledger import replay_evidence


def main():
    root = Path(__file__).resolve().parents[3]
    reports = root / "reports/13-application"
    replay_file = reports / "market-replay.json"
    portable = engine_replay(public_only=True)
    saved = json.loads(replay_file.read_text()) if replay_file.exists() else {}
    if Market().source != portable["source"]:
        saved["local"] = engine_replay()
    saved["portable"] = portable
    replay_file.write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
    paths = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\0")
    )
    release = [root / path for path in paths if path]
    logs = list((root / "data/local/13").glob("*.log"))
    audit = replay_evidence(release_paths=release + logs)
    audit["release_scan"].update(tracked_files=len(release), local_logs=len(logs))
    (reports / "ledger-replay.json").write_text(
        json.dumps(audit, indent=2, allow_nan=False) + "\n"
    )
    print(audit["release_scan"])


if __name__ == "__main__":
    main()
