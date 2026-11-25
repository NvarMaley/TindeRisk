#!/bin/zsh
set -eu
cd "$(dirname "$0")"
[[ -x .venv/bin/python ]] || { echo 'Run INSTALL.command first.'; exit 1; }
echo 'RiskMatch V3: http://127.0.0.1:3001/'
echo 'Keep this Terminal window open while using RiskMatch.'
exec .venv/bin/python -u -c "import sys;sys.path.insert(0,'apps/api');from server import ThreadingHTTPServer,Handler;ThreadingHTTPServer(('127.0.0.1',3001),Handler).serve_forever()"
