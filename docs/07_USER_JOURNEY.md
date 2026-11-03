# Client Journey and Result Presentation

This document is the product specification for the client-facing application. The scientific methodology remains defined in `03_METHODOLOGY.md`; this document defines what the user sees and how decisions are structured.

## 1. Product Principle

RiskMatch does not ask a client to choose an optimization model before establishing an appropriate risk level. The application follows this order:

1. collect capacity, tolerance, horizon, liquidity, knowledge, and constraints;
2. assign a risk category, capped by financial capacity;
3. load precomputed portfolios for that category;
4. compare investment strategies at the same reference risk level;
5. explain historical evidence, advantages, and limitations in plain language;
6. record the client's selection;
7. monitor the selected portfolio with current market prices.

The application supports a decision. It does not predict which strategy will deliver the highest future return and does not provide financial advice.

## 2. Risk Categories

| Category | Volatility band | Reference volatility | Plain-language meaning |
|---|---:|---:|---|
| Conservative | 4%–6% | 5% | Prioritizes capital stability and smaller fluctuations |
| Balanced | 6%–9% | 8% | Accepts moderate fluctuations for long-term growth |
| Growth | 9%–12% | 10% | Accepts meaningful losses and fluctuations for higher growth exposure |
| Aggressive | 12%–15% | 14% | Accepts large fluctuations and potentially severe temporary losses |

The boundaries must be treated consistently: the lower bound is inclusive; the upper bound is exclusive, except for the final band. The continuous profile score, capacity ceiling, and achieved ex-ante volatility are retained for audit and the technical panel. The client-facing result is the category and its range.

If tolerance and capacity disagree, the lower permitted category wins. Constraints may reduce the achieved volatility below the category reference.

## 3. Prepared Portfolio Catalogue

For each validated strategy and each risk category, the offline pipeline produces:

- current target weights;
- a walk-forward historical value series;
- net and gross metrics;
- risk contributions and concentration;
- turnover and modeled costs;
- a short, evidence-based list of advantages and limitations;
- the result date, common comparison period, and configuration version.

The catalogue is indexed by `risk_band × strategy`. Tobin scaling may reuse one risky core across bands; client constraints may require a constrained re-optimization.

## 4. What the Client Sees

Each strategy card shows only five primary measures:

1. historical annualized return, net of modeled costs;
2. realized annualized volatility;
3. net Sharpe ratio;
4. maximum historical drawdown;
5. estimated annualized cost.

The card also contains two or three advantages and limitations. These statements must come from predefined strategy characteristics and validated results, not from whichever strategy has the highest return.

Examples:

- ERC advantage: diversified risk contributions and no direct dependence on expected-return estimates;
- ERC limitation: may allocate heavily to low-volatility assets;
- Classical advantage: explicitly balances estimated risk and return;
- Classical limitation: sensitive to expected-return estimates;
- Black-Litterman advantage: combines a prior with documented views;
- Black-Litterman limitation: depends on the validity and confidence of those views;
- 60/40 advantage: simple, transparent benchmark;
- 60/40 limitation: fixed allocation may not diversify risk equally.

Detailed measures such as Sortino, Calmar, Expected Shortfall, turnover, concentration, tracking error, and risk contributions belong in an optional “Technical details” panel.

## 5. Interpretation Rules

- Use “historical annualized return,” never “promised return.”
- Show net-of-cost results first; gross results are technical details.
- Compare strategies over one common historical period.
- Show longer histories separately and label them as non-comparable.
- Never rank strategies using return alone.
- Do not label a strategy “best.” Explain its trade-offs.
- Display that past performance does not predict future performance.
- Display uncertainty, data dates, assumptions, and known limitations.

## 6. Role of the Backtest

The walk-forward backtest is the scientific validation engine behind the cards. At every historical date it uses only information available at that date. It is not run interactively and is not presented as a forecast.

It establishes whether each prepared strategy:

- stayed close to its reference risk;
- delivered acceptable risk-adjusted performance after costs;
- remained stable across prespecified periods;
- survived crisis periods without hidden future information;
- produced reasonable turnover and concentration.

The user sees a concise summary. The professor can open the technical panel and inspect the complete methodology and diagnostics.

## 7. Selection Record

When a client selects a portfolio, save:

- profile and risk category;
- strategy and catalogue version;
- reference and achieved volatility;
- selection date and initial amount;
- initial prices and target weights;
- constraints and acknowledgements;
- historical metrics shown at selection time.

## 8. Live Monitoring

After selection, the application updates the portfolio using the latest available market prices. Live monitoring is separate from the historical backtest and shows:

- value and return since selection;
- current weights and drift from targets;
- rolling realized volatility and category range;
- current drawdown;
- benchmark comparison;
- rebalancing alerts;
- data timestamp and next scheduled review.

Daily end-of-day updates are sufficient for the academic application. The interface must not imply tick-by-tick execution or brokerage connectivity.

## 9. Acceptance Criteria

The journey is complete when a new user can:

1. understand their category without reading a formula;
2. compare all validated strategies on the same basis;
3. identify at least one advantage and limitation of each choice;
4. distinguish historical evidence from a forecast;
5. make and export a selection;
6. return later and understand performance since selection and whether rebalancing is needed.
