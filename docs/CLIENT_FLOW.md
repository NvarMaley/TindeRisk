# Client presentation and research coverage

The local application keeps its existing logo and lagoon identity. The primary navigation is Mandate → Risk profile → Strategies → My Matches. Research methods and data diagnostics remain available via the separate Research menu.

| Stage | Chapter coverage | Client presentation |
|---|---|---|
| Profile and objectives | 01, 12 | Visible eleven-goal picker, dated goals, priorities and financial capacity; advanced constraints collapsed. |
| Risk profile | 02 | Behavioral questionnaire, summary and optional diagnostic detail. USD/deck limitations are disclosed before proceeding. |
| Research catalogue | 03–11 | Universe, historical coverage, source audit, return/forecast/risk/factor analytics; technical controls remain under Research. |
| Strategy construction and evaluation | 13–24 | Collapsible research modules with historical model diagnostics, baselines, simulation, stress and instrument research. |
| Strategy selection | 25 | Stress-filtered historical cards, clear strategy titles, historical wealth and positions, Like/Dislike, shortlist and funded allocation. |
| Policy simulation and reporting | 26–27 | Confirmed Match, goal assessment, dynamic policies, reconciled simulation export and local encrypted saves. |

Historical Matching currently supports the USD research archive and supported stress-only mandate constraints. CHF remains available for mandate/objective research; unsupported constraints are disclosed without relaxing them. The model catalog is warmed during Discovery, with a single shared computation under concurrent requests. The client sees loading, empty and retry states. Source audits display progressively.

The local server version marker is `client_flow: 28`. Starting the existing launcher detects the obsolete process and invokes the project-specific restart script on the host. An outdated server does not discard saved choices or simulate missing endpoints.

## Local verification (2026-11-25)

Representative actual USD handler workflow: mandate preview, catalogue preparation, Discovery session and score, 21 historical cards, manual allocation, optimized allocation, goal assessment, dynamic report and ZIP export all returned 200. Preparation took approximately 1.42 seconds; already prepared cards 0.002 seconds, allocation 0.008–0.009 seconds, goals 0.046 seconds, dynamic and export around 1.4 seconds on the test machine. These are measured observations, not latency guarantees.

The research handler smoke run returned 200 for universe, sources, snapshot, returns, statistics catalogue, forecast/risk/factor/tail universe, baselines, mean–variance, Black–Litterman, hierarchical, downside, advanced, long-only, alternative, Treasury, archived futures, walk-forward, stress, matching research and improvement. Some audits took 10–31 seconds; their results are distinct from investability approval. Browser interaction tests cover the client workflow. Actual local HTTP/browser verification requires restarting on the host because this environment cannot bind or connect to loopback sockets.
