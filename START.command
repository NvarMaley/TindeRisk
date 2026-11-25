#!/bin/zsh
set -eu
setopt NO_BG_NICE
cd "$(dirname "$0")"
[[ -x .venv/bin/python ]] || ./INSTALL.command
.venv/bin/python -c 'import sys, pathlib; assert sys.version_info[:2] == (3, 12); assert "include-system-site-packages = false" in (pathlib.Path(sys.prefix) / "pyvenv.cfg").read_text()' || { echo 'Run INSTALL.command to set up the isolated Python 3.12 environment.'; exit 1; }
mkdir -p .run/jupyter-runtime
export JUPYTER_RUNTIME_DIR="$PWD/.run/jupyter-runtime"
export IPYTHONDIR="$PWD/.run/ipython"
start_service() {
  local name="$1"; shift
  if [[ -f ".run/$name.pid" ]] && kill -0 "$( < ".run/$name.pid" )" 2>/dev/null; then
    if [[ "$name" = web ]]; then
      # The existing process may still use Python code from a previous version.
      if ! curl --noproxy '*' --silent --fail --max-time 2 http://127.0.0.1:3000/api/health | .venv/bin/python -c 'import json,sys; assert json.load(sys.stdin).get("client_flow")==30' 2>/dev/null; then
        ./RESTART_WEB.command
        return
      fi
    fi
    echo "$name already running"; return
  fi
  nohup "$@" </dev/null >".run/$name.log" 2>&1 &
  local pid=$!
  printf '%s\n' "$pid" >".run/$name.pid"
}
start_service web .venv/bin/python apps/api/server.py
start_service jupyter .venv/bin/python -m jupyterlab --ip=127.0.0.1 --port=8888 --ServerApp.port_retries=0 --no-browser --ServerApp.root_dir="$PWD"
wait_ready() {
  local name="$1" url="$2"
  local attempt
  for attempt in {1..30}; do
    if curl --silent --fail --max-time 1 --output /dev/null "$url"; then
      return 0
    fi
    if ! kill -0 "$( < ".run/$name.pid" )" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  echo "$name: startup failed or health check timed out; see .run/$name.log"
  return 1
}
wait_ready web http://127.0.0.1:3000/api/health
wait_ready jupyter http://127.0.0.1:8888/lab
echo "Web : http://127.0.0.1:3000"
echo "Jupyter: see .run/jupyter.log for the token-authenticated link."
open http://127.0.0.1:3000 || true
