"""Check path-level privacy guardrails without opening datasets or credentials."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
for path in tracked:
    assert not path.startswith((".venv/", ".venv-", ".run/", "_source/")), path
    assert not path.startswith("data/") or path == "data/README.md", path
    assert not path.startswith(".env") or path == ".env.example", path
    assert not path.endswith((".parquet", ".duckdb", ".sqlite", ".sqlite3")), path
for path in ("data/raw/example.csv", "data/data/wrds.csv", ".run/example.log", ".env.local",
             ".venv/bin/python", ".venv-legacy/bin/python"):
    subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT, check=True)
print("Git path exclusions verified; this is not a license or secret-content audit.")
