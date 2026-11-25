# Client presentation and research coverage

The local application keeps its existing logo and lagoon identity. The primary navigation is Mandate → Risk profile → Strategies → My Matches. Research methods and data diagnostics remain available via the separate Research menu.

| Stage | Chapter coverage | Client presentation |
|---|---|---|
| Profile and objectives | 01, 12 | Visible eleven-goal picker, dated goals, priorities and financial capacity; advanced constraints collapsed. |
| Risk profile | 02 | Behavioral questionnaire, summary and optional diagnostic detail. USD/deck limitations are disclosed before proceeding. |
| Research catalogue | 03–11 | Universe, historical coverage, source audit, return/forecast/risk/factor analytics; technical controls remain under Research. |
| Strategy construction and evaluation | 13–24 | Collapsible research modules with historical model diagnostics, baselines, simulation, stress and instrument research. |
| Strategy selection | 25 | Mandate-conditioned construction, stress and asset-cap validation, historical wealth, goal projections, positions, Like/Dislike and funded allocation. |
| Policy simulation and reporting | 26–27 | Confirmed Match, goal assessment, dynamic policies, reconciled simulation export and local encrypted saves. |

Personalized Matching uses the common USD research panel. Supported hard constraints
include asset-class restrictions, per-asset caps, modeled stress, modeled volatility
and the funded gross/net budget. CHF remains available for mandate/objective research.
See [personalized construction](PERSONALIZED_MATCHING.md). The common market inputs
are warmed during Discovery; each client receives a newly constructed versioned deck.
The client sees loading, empty and retry states.

The local server version marker is `client_flow: 29`. Starting the existing launcher detects the obsolete process and invokes the project-specific restart script on the host. An outdated server does not discard saved choices or simulate missing endpoints.

## Local verification (2026-11-25)

The earlier five-ETF prototype returned 21 cards for the example mandate.
The personalized engine now makes a separate construction pass and caches
the result by mandate and aversion; the historical notebook exercises
two risk scores and a restricted Treasury mandate, plus allocation,
goal assessment, dynamic report and ZIP export.

The research handler smoke run returned 200 for universe, sources, snapshot, returns, statistics catalogue, forecast/risk/factor/tail universe, baselines, mean–variance, Black–Litterman, hierarchical, downside, advanced, long-only, alternative, Treasury, archived futures, walk-forward, stress, matching research and improvement. Some audits took 10–31 seconds; their results are distinct from investability approval. Browser interaction tests cover the client workflow. Actual local HTTP/browser verification requires restarting on the host because this environment cannot bind or connect to loopback sockets.
