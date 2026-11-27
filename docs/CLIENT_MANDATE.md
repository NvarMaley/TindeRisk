# Client Mandate — Chapter 01

Version 2.0.0, simulation only. Implementation: `src/riskmatch/profiling/mandate.py`; API: `POST /api/mandate/preview`; form: `apps/web/mandate.js`. SciPy is now a runtime dependency for the dated cash-flow solver; its pinned version is unchanged. A structural validation is not a suitability assessment, financial advice, market feasibility, or approval to trade. Use fictional profiles only.

## Formulaire client actuel

- Le parcours USD présente dix objectifs. « Croissance » couvre `OBJ05` et le même comportement de classement que l'ancien `OBJ06`. Les sauvegardes existantes restent lisibles. Une fiche `OBJ06` s'affiche comme « Croissance » lors de la révision du mandat et utilise `OBJ05` lors de la nouvelle confirmation.
- « Revenu » renvoie vers les retraits mensuels ou ponctuels. La couverture dépend de ces flux. Le formulaire masque le montant, la devise, la base et la pénalité de cet objectif.
- Les autres actifs et les dettes se trouvent dans **Bilan patrimonial facultatif**. Le solde à investir, les liquidités, les placements disponibles, la réserve et les flux restent dans le parcours principal.
- La pénalité de déficit demeure accessible dans les réglages avancés d'un objectif chiffré, avec 1 par défaut. L'inflation apparaît pour une cible réelle ou un objectif de protection contre l'inflation. Le taux de change apparaît pour une cible chiffrée en devise étrangère.
- Les deux questions de perte restent distinctes. Les choix d'actifs couvrent actions américaines et ETF d'actions, ETF du Trésor américain et cash USD. La volatilité et le plafond par actif sont facultatifs, avec les modes « À respecter absolument » et « À privilégier ».
- Le serveur conserve les onze identifiants et les champs hérités du schéma pour la lecture des anciennes sauvegardes et les modules de recherche. Les classes retirées bloquent le nouveau calcul personnalisé jusqu'à la révision du mandat.

## Data and units (CH01.01–05)

| Input | Unit / interpretation |
|---|---|
| Reference currency | CHF or USD; all balance sheet amounts and recurring/dated flows use this currency |
| FX | Optional CHF per USD scenario; USD→CHF multiply, CHF→USD divide; required for mixed-currency goal amounts, no forecast |
| Inflation | Effective annual decimal rate, explicitly required for real goals; target nominal amount = real amount × (1+inflation)^years |
| Wealth | cash + liquid investments + other assets − debt; reserve is already included in cash |
| Investable wealth | cash + liquid investments − emergency reserve; allocated capital is a subset, not an additional asset |
| Income and expenses | Monthly net income and spending; surplus = income − spending; contributions cannot exceed positive surplus in the initial model |
| Flows | Positive contributions, negative withdrawals/liability payments; recurring monthly from the valuation date; explicit dated events must lie inside horizon |
| Horizon | Valuation and end date, ACT/365.25 year fraction; next withdrawal (including funded goals) is separate |
| Goals | Catalog ID, due date, optional amount, currency, nominal/real basis, priority 1–5, nonnegative relative shortfall penalty, explicit funded obligation flag |

Do not double count liabilities in monthly expenses, dated flows and goal obligations. Debt balance reduces net worth; debt repayment timing is a separate dated cash-flow input. The 11 objectives retain their stable catalog IDs. Income is periodic; never treat it as a terminal liability. Goal-Based and LDI require an explicitly funded dated target. Other styles may be non-financial preferences or an explicit funded monetary obligation. A monetary target for a non-funded objective is assessed independently; funded objectives are combined into the cash-flow schedule. Priority weights are priority divided by sum of priorities; penalty is a separate dimensionless multiplier, reserved for normalized shortfall scoring in chapter 12. Objective definitions do not select an optimizer or a benchmark.

| ID | Client intent | Quantitative target to implement later |
|---|---|---|
| OBJ01 | Capital preservation | Minimize probability and magnitude of nominal/real loss |
| OBJ02 | Recurring income | Net periodic income target and stability; withdrawals are cash flows |
| OBJ03 | Conservative | Strict loss/volatility budget, with return secondary |
| OBJ04 | Balanced | Risk-return trade-off constrained by mandate |
| OBJ05 | Growth | Terminal wealth or real return, not automatic leverage |
| OBJ06 | Aggressive growth (legacy ID) | Same orientation and scoring rule as OBJ05 in personalized matching |
| OBJ07 | Inflation protection | Purchasing-power target and inflation sensitivity |
| OBJ08 | Absolute return | Net excess return versus cash and downside control |
| OBJ09 | Liability-driven | Dated liability coverage; duration/DV01 mismatch later |
| OBJ10 | Goal-based | Funding success probability and expected shortfall later |
| OBJ11 | Capital protection | Conditional floor, gap risk and hedge costs; no guarantee |

## Deterministic funding mathematics (CH01.06)

At constant annual effective nominal return r, dated deposits and withdrawals satisfy

`W(T) = C(1+r)^T + Σ CF_i (1+r)^(T−t_i)`.

Without flows, `r = (G/C)^(1/T)−1`. With flows, solve the discounted cash-flow equation with Brent's method in log(1+r) on [−20, 20], after grouping same-date flows. More than one chronological sign change produces an explicit ambiguous-root diagnostic, not a selected IRR. A root implying intermediate borrowing is rejected. Individual zero-return gap = max(0, target − capital available by its date); separately report the aggregate scheduled balance including all funded goals, without double counting. Zero-return deficit is a warning rather than proof that market funding is impossible. A required return is not a forecast or required volatility. No inflation forecasts or FX forecasts are inferred.

## Ability, willingness and required risk (CH01.07–08)

The client declares maximum financially absorbable loss in currency units. Cap it by allocated capital, investable wealth and the minimum modeled zero-return balance over the next 12 months (or shorter horizon). The effective hypothetical stress cap is the minimum of declared stress limit, hard loss budget and capacity/capital. This is a conservative deterministic screening rule, not an empirical capacity model. No behavior score or return target increases the cap. Willingness is measured separately in chapter 02; required risk needs a validated return/risk engine. Technical knowledge (none/basic/advanced) and practical experience (none/limited/experienced) are self-reported separately for equity, Treasuries, futures, leverage, and short selling; absence of either conflicts with advanced permission. It is not a qualification test.

## Restrictions and feasibility (CH01.09–12)

Hard stress and loss budgets are required and share one input in new drafts. The current form offers annual volatility and per-holding weight limits. Historical payloads can also carry issuer/sector, turnover, cost, liquidity or exposure limits, ESG/tax/FX preferences and advanced permissions. The personalized engine handles the [current portfolio universe and supported constraints](PERSONALIZED_MATCHING.md). A required restriction outside that scope blocks personalized generation. Null means the optional limit is unspecified. Capital above investable wealth, contributions above surplus and uncovered spending deficits are structural conflicts.

## Versioning, consent and UI (CH01.13–15)

Schema version 2.0.0 covers both the client and constraint payload; the previous minimal schema is preserved only for old simulation saves. The browser stores the confirmed payload locally using the existing encrypted save mechanism; a four-digit PIN is not for real client information. Draft preview does not replace the confirmed mandate. Explicit confirmation updates the save and resets discovery/portfolio choices; before/after review displays the old and proposed stress cap, capital and dated goals. Conflicts disable confirmation. The API validates on both preview and candidate requests; it stores no profile. EN/FR labels preserve canonical English API keys. `configs/mandate-example.json` is wholly synthetic. Tests cover balances, dated returns, FX/inflation, constraints, no short/leverage inference, malformed amounts, negative/zero capital, unsupported currency, missing consent, horizon mismatch, uncovered withdrawals, and UI confirmation; CI executes synthetic notebook cells only.

## Decision log — provisional assumptions for owner review

- CHF/USD only, mixed goals use an explicit scenario FX rate, no live FX conversion.
- Loss capacity uses a 12-month minimum zero-return liquidity cushion, not a psychometric or regulated capacity assessment.
- Recurring contributions are funded by positive monthly surplus; reserve is part of cash. Dated obligations are kept separate from debt stock.
- Goal priorities 1–5 and separate shortfall penalty; all amounts nominal by default unless explicitly real.
- No advanced permission by default; optional hard restrictions block demo Explore until they are evaluated. No real financial data, recommendations or orders.
