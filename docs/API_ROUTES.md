# Chapter 27 — API route contract

The local API is JSON over loopback HTTP. Research commands are POST requests with explicit inputs; all selected data versions and mandates are checked by the relevant engine. No server profile record is created. The encrypted browser save holds the profile, Discovery responses, candidate IDs, swipes and paper confirmation. Repeating a pure calculation with the same inputs and frozen versions is safe. The paper export returns a content-addressed ZIP.

| Local action | Existing route | Request and result |
|---|---|---|
| Profile / mandate | POST /api/mandate/preview | Versioned mandate JSON → structural feasibility and typed goals |
| Discovery session and cards | POST /api/discovery/session | Seed and currency → versioned randomized card bank |
| Discovery responses | POST /api/discovery/score | Seed, currency, answers, optional confidence/locales → score, coverage and sensitivity |
| Risk reports | POST /api/risk/asset, /api/risk/matrix, /api/tail/universe/asset, /api/tail/matrix | Asset identity or aligned series, date/currency → research risk diagnostics |
| Portfolio run | POST /api/baselines, /api/mean-variance, /api/black-litterman, /api/hierarchical, /api/downside, /api/advanced, /api/long-only, /api/alternative, /api/walk-forward, /api/stress-mc | Dated research configuration → model diagnostics and candidate research results |
| Candidate deck | POST /api/matching/cards | Mandate and aversion → stress-filtered historical candidate cards and deck version |
| Swipe | Local encrypted save | Choice and candidate identity, scoped to deck version |
| Allocation and paper selection | POST /api/match-allocations/evaluate, /api/match-allocations/optimize | Mandate, sleeve names, version and budgets → validated experimental allocation; explicit paper confirmation saved locally |
| Goal assessment | POST /api/matching/goals | Confirmed historical allocation and full mandate → paired conditional objective results |
| Dynamic simulation | POST /api/dynamic | Dated allocation, fee and frequency → policy ledger and sensitivity |
| Paper export | POST /api/paper/export | Same inputs and selected policy → reconciled ZIP and run ID |

## Future resource API definition

The multi-user architecture is separate from the local research runner. Define authenticated resources: POST /api/profiles, PATCH /api/profiles/{profile_id}; POST /api/profiles/{profile_id}/sessions, GET /api/sessions/{session_id}/cards, PUT /api/sessions/{session_id}/responses/{card_id}; GET /api/profiles/{profile_id}/risk-reports/{run_id}; POST /api/profiles/{profile_id}/portfolio-runs, GET /api/portfolio-runs/{run_id}/candidates, PUT /api/portfolio-runs/{run_id}/swipes/{candidate_id}; POST /api/portfolio-runs/{run_id}/paper-selections. Every resource must be owned by or delegated to the authenticated profile owner, checked server-side before reading or changing it. Repeated PUT requests replace the same resource; POST commands require an owner-scoped idempotency key and payload hash. Retain version IDs and reject stale mandates/candidates with a conflict response. These resource paths are a design contract, not deployed endpoints; CH27.08 remains open until authorization and persistence are implemented and tested. No real-order route is defined.
