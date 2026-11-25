# Local V3 API

Python HTTP prototype: `python apps/api/server.py` (port 3000, loopback). GET /api/health, GET /api/cards, POST /api/score, POST /api/candidates. Canonical values are English; card responses include French presentation text. No server-side persistence, multi-user authentication or execution. Do not expose outside localhost.
