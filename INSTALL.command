#!/bin/zsh
set -eu
cd "$(dirname "$0")"
python3.12 -c 'import sys; assert sys.version_info[:2] == (3, 12)' || { echo 'Install Python 3.12 first.'; exit 1; }
if [[ -d .venv ]] && ! .venv/bin/python -c 'import sys, pathlib; assert sys.version_info[:2] == (3, 12); assert "include-system-site-packages = false" in (pathlib.Path(sys.prefix) / "pyvenv.cfg").read_text()'; then
  echo 'Legacy environment detected. Stop RiskMatch, then rename .venv to .venv-legacy and rerun this installer.'
  exit 1
fi
[[ -d .venv ]] || python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install -r requirements-forecast.txt
.venv/bin/python -m pip install -r requirements-risk.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/python -m pytest
echo "Installation complete. Double-click START.command."
