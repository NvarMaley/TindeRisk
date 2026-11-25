#!/bin/zsh
set -eu
setopt NO_BG_NICE
cd "$(dirname "$0")"
[[ -x .venv/bin/python ]] || { echo 'Run INSTALL.command first.'; exit 1; }
mkdir -p .run
if [[ -f .run/web.pid ]]; then
  pid=$(<.run/web.pid)
  if [[ "$pid" = <-> ]] && kill -0 "$pid" 2>/dev/null; then
    command=$(ps -p "$pid" -o command=)
    if [[ "$command" != *apps/api/server.py* ]]; then
      echo "Unrecognized server PID $pid; no process stopped."
      exit 1
    fi
    kill "$pid"
    for attempt in {1..20}; do
      if ! kill -0 "$pid" 2>/dev/null; then break; fi
      sleep 1
    done
  fi
fi
if lsof -nP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 3000 is still occupied. No other process will be stopped."
  exit 1
fi
echo "Starting the latest RiskMatch V3 server..."
nohup .venv/bin/python -u apps/api/server.py </dev/null >>.run/web.log 2>&1 &
pid=$!
printf '%s\n' "$pid" >.run/web.pid
for attempt in {1..120}; do
  if curl --noproxy '*' --silent --fail --max-time 1 http://127.0.0.1:3000/api/health | .venv/bin/python -c 'import json,sys; assert json.load(sys.stdin).get("client_flow")==28' 2>/dev/null; then
    echo "RiskMatch ready: http://127.0.0.1:3000/"
    open http://127.0.0.1:3000/
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 1
done
echo "Startup failed or timed out. Details: .run/web.log"
tail -20 .run/web.log
exit 1
