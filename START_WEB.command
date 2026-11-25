#!/bin/zsh
set -eu
cd "$(dirname "$0")"
if [[ "${1:-}" = "--recover-3001" ]]; then
  echo 'Open http://127.0.0.1:3001 in your original browser and export your encrypted saves. Import the file at http://127.0.0.1:3000.'
  exec .venv/bin/python -u -c "import sys;sys.path.insert(0,'apps/api');from server import ThreadingHTTPServer,Handler;ThreadingHTTPServer(('127.0.0.1',3001),Handler).serve_forever()"
fi
exec ./RESTART_WEB.command
