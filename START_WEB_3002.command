#!/bin/zsh
set -eu
cd "$(dirname "$0")"
if curl -fsS --max-time 2 http://127.0.0.1:3002/api/health >/dev/null; then
  open http://127.0.0.1:3002/
  exit 0
fi
echo 'RiskMatch — http://127.0.0.1:3002/'
echo 'Keep this Terminal window open while using RiskMatch.'
exec .venv/bin/python -u -c "import sys; sys.path.insert(0, 'apps/api'); from server import Handler, ThreadingHTTPServer; ThreadingHTTPServer(('127.0.0.1', 3002), Handler).serve_forever()"
