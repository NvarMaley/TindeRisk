#!/bin/zsh
set -eu
cd "$(dirname "$0")"
for service in web jupyter; do
  file=".run/$service.pid"
  if [[ -f "$file" ]]; then
    pid=$(<"$file")
    command=$(ps -p "$pid" -o command= 2>/dev/null || true)
    if [[ "$service" = web && "$command" = *apps/api/server.py* ]] || [[ "$service" = jupyter && "$command" = *jupyterlab* ]]; then
      kill "$pid" 2>/dev/null || true
      echo "$service stopped"
    else
      echo "$service: unrecognized process; no forced stop."
    fi
  fi
done
