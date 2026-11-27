# Client presentation and research coverage

The local application keeps its existing logo and lagoon identity. The primary navigation is Mandate → Risk profile → Strategies → My Matches. The Research menu contains Universe, Sources, Strategy catalogue and Methodology. Chapter experiments remain available in the notebook.

| Stage | Chapter coverage | Client presentation |
|---|---|---|
| Profile and objectives | 01, 12 | Ten visible goals, dated targets, priorities and financial capacity. The balance-sheet additions and technical limits are optional and collapsed. |
| Risk profile | 02 | Behavioral questionnaire, summary and optional diagnostic detail. USD/deck limitations are disclosed before proceeding. |
| Research catalogue | 03–11 | Universe, historical coverage, source audit, return/forecast/risk/factor analytics; technical controls remain under Research. |
| Strategy construction and evaluation | 13–24 | The strategy catalogue explains each method. The notebook contains the technical experiments and comparisons. |
| Strategy selection | 25 | Mandate-conditioned construction, stress and asset-cap validation, historical wealth, goal projections, positions, Like/Dislike and funded allocation. |
| Policy simulation and reporting | 26–27 | Confirmed Match, goal assessment, dynamic policies, reconciled simulation export and local encrypted saves. |

Personalized Matching and the client Universe tab use the same dated USD universe. Listed securities require 60 consecutive monthly total returns before allocation. USD cash uses the Fama–French monthly risk-free proxy. Supported hard constraints
include asset-class restrictions, per-asset caps, modeled stress, modeled volatility
and the funded gross/net budget. CHF remains available for mandate/objective research.
See [personalized construction](PERSONALIZED_MATCHING.md). The common market inputs
are warmed during Discovery; each client receives a newly constructed versioned deck.
The client sees loading, empty and retry states.

Discovery uses 30 fixed cards. Twenty feed the prudence index. Eight give
experimental loss-aversion intervals, shown under four hypotheses, and two
are comprehension and repeat-choice checks. Matching uses the prudence
index and mandate to obtain the separate variance coefficient `1 + 13.3 q²`.
See [Discovery](RISKMATCH_BEHAVIORAL.md) and the [current mandate form](CLIENT_MANDATE.md#formulaire-client-actuel).

The local server version marker is `client_flow: 30`. Starting the existing launcher detects the obsolete process and invokes the project-specific restart script on the host. An outdated server does not discard saved choices or simulate missing endpoints.

## Local verification (2026-11-25)

The earlier five-ETF prototype returned 21 cards for the example mandate.
The personalized engine now makes a separate construction pass and caches
the result by mandate and aversion; the historical notebook exercises
two risk scores and a restricted Treasury mandate, plus allocation,
goal assessment, dynamic report and ZIP export.

The research handler smoke run returned 200 for universe, sources, snapshot, returns, statistics catalogue, forecast/risk/factor/tail universe, baselines, mean–variance, Black–Litterman, hierarchical, downside, advanced, long-only, alternative, Treasury, archived futures, walk-forward, stress, matching research and improvement. Some audits took 10–31 seconds; their results are distinct from investability approval. Browser interaction tests cover the client workflow. A new full mandate checks the backend engine version before accepting any cards. Local verification on 26 November used the corrected loopback server, the treasury-only and cash-only cases, and the reconciled paper export.
