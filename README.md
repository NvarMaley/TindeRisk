# 💘 RiskMatch — QARM II Project (HEC Lausanne)

> **Swipe your risk. Choose your portfolio. Track it.**
> A Streamlit web app that (1) structures a client's risk capacity, tolerance, and constraints, (2) assigns a plain-language risk category, (3) compares QARM portfolios prepared at that category's reference risk using historical ratios and clear trade-offs, and then (4) tracks the selected portfolio from its selection date.

This README is the project's reference document: it explains **the objective, methodology, and every step from A to Z**.
- The task checklist is in [`CHECKLIST.md`](CHECKLIST.md).
- The step-by-step execution notebook is [`RiskMatch_pipeline.ipynb`](RiskMatch_pipeline.ipynb): **each substep = one cell**, using the **same numbering** as this README and the checklist.
- The collaboration rules are in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- The framework, course alignment, methodology, and exact execution order are in [`docs/`](docs/README.md).

> **Project priority:** the graded core consists of QARM optimization, its validation, and a reliable app. The adaptive questionnaire, HMM regimes, and Fed NLP are conditional extensions. They must be enabled only after validating the core described in [`docs/01_PROJECT_FRAMEWORK.md`](docs/01_PROJECT_FRAMEWORK.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app/Home.py
```

Available shortcuts: `make install`, `make test`, `make app`, and `make check`.

Launching opens the application in the browser. The prototype starts with a lightweight interface; compute-intensive operations (data, regimes, backtests) will run in the notebook and then be exported to `results/`.

## Project governance documents

| Document | Purpose |
|---|---|
| [`docs/01_PROJECT_FRAMEWORK.md`](docs/01_PROJECT_FRAMEWORK.md) | Official brief, scope, compliance, and success criteria |
| [`docs/02_COURSE_ALIGNMENT.md`](docs/02_COURSE_ALIGNMENT.md) | Traceability to QARM, econometrics, data science, client finance, and ESG |
| [`docs/03_METHODOLOGY.md`](docs/03_METHODOLOGY.md) | Data, model, validation, backtest, and testing protocol |
| [`docs/04_EXECUTION_PLAN.md`](docs/04_EXECUTION_PLAN.md) | Phase order, dependencies, and definition of done |
| [`docs/05_DECISIONS.md`](docs/05_DECISIONS.md) | Open decisions and assumptions to finalize |
| [`docs/07_USER_JOURNEY.md`](docs/07_USER_JOURNEY.md) | Official client journey, risk bands, comparison cards, and monitoring |

---

## Table of contents

0. [Project objective and instructor expectations](#0-project-objective-and-instructor-expectations)
1. [Architecture overview](#1-architecture-overview)
2. [Conventions and notation](#2-conventions-and-notation)
3. [Step 1 — Data collection](#step-1--data-collection)
4. [Step 2 — Exploration and estimation](#step-2--exploration-and-estimation)
5. [Step 3 — Client profile: baseline, then adaptive](#step-3--client-profile-baseline-then-adaptive)
6. [Step 4 — Signals: sentiment, Fed, and regimes](#step-4--signals-sentiment-fed-and-regimes)
7. [Step 5 — Portfolio construction](#step-5--portfolio-construction)
8. [Step 6 — Backtesting](#step-6--backtesting)
9. [Step 7 — Client selection and monitoring](#step-7--client-selection-and-monitoring)
10. [Step 8 — The Streamlit web app](#step-8--the-streamlit-web-app)
11. [Step 9 — The pitch](#step-9--the-pitch)
12. [Repository structure](#repository-structure)
13. [Role allocation](#role-allocation)
14. [Pitfalls to avoid](#pitfalls-to-avoid)
15. [References](#references)

---

## 0. Project objective and instructor expectations

**Brief** ("Projects" slides, M.-A. Divernois): *“Design an investment strategy and build your own portfolio management web app.”*
- Deliverables: **code on GitHub + link to a Streamlit app**. No report.
- Presentation: 15 minutes per group. The instructor plays the **client**.
- Required: use **quantitative optimization and the course tools**. Bonus: an **interesting or fun** idea/data.

**Grading rubric** and our response:

| Area | Criteria | RiskMatch |
|---|---|---|
| Content | Client/data complexity · addresses client needs · course topics | Client profile + constraints + Markowitz/LW + ERC/RB + BL/StockTwits + benchmark |
| Presentation | Clarity · answers to live questions | The instructor completes the questionnaire; every technical choice is justified by the course |
| Web app | Design/interactivity · completeness · no bugs | 4 pages, compute-intensive operations precomputed, lightweight app |

**Our thesis:** a client's primary question is not “which portfolio?” but “**what level of risk can I reasonably take?**” RiskMatch first assigns a transparent risk category, then shows several investment philosophies prepared at that category's same reference risk. The client chooses from clear historical evidence and trade-offs, not from a promised return.

---

## 1. Architecture overview

```
┌───────────────────────── OFFLINE (notebook / scripts, once) ─────────────────────────────┐
│ 1. Data: ETF prices, risk-free rate, FRED macro data, StockTwits sentiment, FOMC          │
│ 2. Estimation: returns, Σ (Ledoit-Wolf), μ (conservative), long-term Sharpe               │
│ 3. Questionnaire: capacity + tolerance → risk category; adaptive engine is an extension │
│ 4. Signals: StockTwits polarity → BL views; Fed and regimes = extensions                  │
│ 5. Risky cores: Classic, ERC, BL, benchmark; Chameleon as an extension                    │
│ 6. Walk-forward validation → prepared catalogue by risk band × strategy                   │
└──────────────────────────────────────────┬───────────────────────────────────────────────┘
                                           │ .parquet / .json files
┌─────────────────────────────── ONLINE (Streamlit app) ────────────────────────────────────┐
│ Page 1 Profile   : questionnaire → category, range, capacity cap, constraints             │
│ Page 2 Portfolios: simple cards at the category reference risk + pros/cons                │
│ Page 3 Analysis  : optional technical ratios, weights, risk contributions, evidence       │
│ Page 4 Monitoring: performance since selection, drift, risk and rebalance alerts          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Conventions and notation

**Note the course notation** (LN1, LN4): in the γ problem, **γ multiplies μ**—it is a risk **tolerance**. **Aversion** is **φ = 1/γ**. We use this convention throughout:

| Symbol | Meaning |
|---|---|
| φ | client's risk aversion (estimated by the questionnaire); γ = 1/φ |
| σ* | internal annualized volatility calibration; mapped to a client-facing risk band |
| x | weight vector; x_risky = a strategy's risky “core” |
| Σ, μ | covariance and expected returns (annualized) |
| r | risk-free rate |
| SR | Sharpe ratio |
| P, Q, Ω, τ | Black-Litterman views (LN4) |
| RC_i, RC*_i | absolute / relative risk contributions (LN5) |

Other conventions:
- **Frequency:** **daily** returns to estimate Σ, **monthly rebalancing** (last business day of the month).
- **Annualization:** × 252 (means), × √252 (volatilities).
- **Currency:** USD (the ETFs are denominated in USD). For the CHF option, see the pitfalls section.
- **Fixed random seed** (`SEED = 42`) for every simulation.

---

## Step 1 — Data collection

**Objective:** obtain all raw data, clean and align it, and save it locally. **All sources are free.**

### 1.1 ETF prices (yfinance)

| Asset group | Tickers | Purpose |
|---|---|---|
| Equities — 9 long-established SPDR sectors | `XLK XLF XLE XLV XLY XLP XLI XLB XLU` | investable universe + link to sector sentiment |
| US Treasury bonds | `IEF` (7–10 years), `TLT` (20+ years) | diversification, crisis regime |
| Gold | `GLD` | safe-haven asset |
| Benchmark only | `SPY` | reference 60/40 portfolio (with `IEF`) |

- Download **adjusted prices** (including dividends): `yf.download(tickers, start="2005-01-01", auto_adjust=True)`.
- Why these 9 sectors: `XLRE` (2015) and `XLC` (2018) do not exist over the full period.
- Study period: **2006 → present** (a 3-year estimation window means backtests begin around 2009).

### 1.2 Risk-free rate (FRED)
- `DTB3` series (3-month T-bill, annual %). Convert to a daily rate: `r_jour = DTB3/100/252`.
- Access without an API key: `pandas_datareader.data.DataReader("DTB3", "fred", start)` or the CSV URL `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3`.

### 1.3 Macro variables (FRED) — for regimes
Initial list (to be finalized in Step 4.4):

| Series | Content | Transformation |
|---|---|---|
| `T10Y2Y` | 10y–2y yield-curve slope | level |
| `BAA10Y` | Baa–10y credit spread | level |
| `VIXCLS` | VIX | log |
| `CPIAUCSL` | inflation (CPI) | 12-month change |
| `UNRATE` | unemployment | 12-month change |
| `INDPRO` | industrial production | 12-month change |

⚠️ **Release dates:** monthly series (CPI, unemployment) are published **with a delay**. Lag them by **at least 1 month** to avoid look-ahead bias.

### 1.4 StockTwits sentiment (provided by the instructor)
- LN7 lab file (`sentratio_and_price_*.pkl`): by ticker and day, `Nbullish`, `Nbearish`, `N`, and price.
- Coverage: **2010 → March 2020** (see LN7). **Confirm with the instructor:** list of firms, raw text or counts only.
- We will need a **firm → GICS sector mapping table** (to aggregate to our 9 sector ETFs). Free source: SPDR ETF holdings on the SSGA website, or the S&P 500 company list (Wikipedia), which includes GICS sectors.

### 1.5 Federal Reserve communications (FOMC)
- Statements and minutes: Federal Reserve website (`federalreserve.gov`, FOMC section).
- Shortcut: the annotated dataset from the *Trillion Dollar Words* paper (GitHub `gtfintechlab/fomc-hawkish-dovish`) and the `gtfintechlab/FOMC-RoBERTa` model (Hugging Face, CC BY-NC 4.0 license—suitable for an academic project).
- Retain for each document: **publication date**, type (statement / minutes / press conference), and text.

### 1.6 Cleaning and alignment
- Common index = **NYSE trading days**. Forward-fill **only** macro series (never prices).
- Check for missing values, duplicates, and abnormal jumps (> 25% in one day for an ETF is suspicious).
- Returns: **simple** returns for portfolios; log returns may be used for statistics.

### 1.7 Storage
- `data/raw/`: raw downloads (never modify).
- `data/processed/`: `prices.parquet`, `returns.parquet`, `rf.parquet`, `macro.parquet`, `sentiment_sector.parquet`, `fomc.parquet`.
- A `data/README_data.md` recording **download date, source, and transformations**.

---

## Step 2 — Exploration and estimation

**Objective:** understand the data and produce **robust** estimators (LN3).

### 2.1 Descriptive statistics
Annualized return and volatility, Sharpe, skewness, kurtosis, and maximum drawdown by asset; correlation heatmap; rolling equity/bond correlations (their sign changes across regimes—show this in the pitch).

### 2.2 Covariance Σ
- **3-year** rolling window of daily returns.
- **Ledoit-Wolf shrinkage** (LN3): `sklearn.covariance.LedoitWolf` or a custom implementation toward the constant-correlation target (course material).
- Compare sample vs. shrunk covariance: matrix conditioning and stability of GMV weights (demonstrating the instability discussed in LN3).

### 2.3 Expected returns μ (the weak link)
μ is used only by “The Classic.” It requires a **conservative** estimator:
- Option A: historical mean **shrunk** toward the cross-sectional mean (James-Stein type).
- Option B: implied equilibrium μ (reverse optimization, LN4)—in this case, Classic and BL-without-views coincide, providing a useful control.
- Document the choice. **Never** use the raw mean over the entire period (look-ahead).

### 2.4 “Long-term” Sharpe for profiling
The φ → σ* mapping (Step 3.8) requires a **reference Sharpe ratio** for the risky portfolio. We use a **conservative and stable assumption** (e.g., SR = 0.35, justified using the statistics in 2.1) rather than a noisy estimate. Perform sensitivity analysis.

---

## Step 3 — Client profile: baseline, then adaptive

**MVP objective:** produce a transparent, reproducible client profile that separates capacity, tolerance, knowledge, and constraints. Start with 10 to 15 fixed questions. Adaptive selection from a bank of 60 is an **extension**, enabled only if it outperforms the baseline and passes a real user test.

### 3.0 General principle

We distinguish three concepts (as also required by suitability regulations: MiFID II in the EU / FinSA in Switzerland):

| Dimension | Question | Nature |
|---|---|---|
| Risk **tolerance** | “how much risk do you *want* to take?” | psychological → **estimated** (adaptive) |
| Risk **capacity** | “how much risk can you *afford* to take?” | objective (horizon, liquidity, maximum loss) → **rules** |
| **Constraints** | “what do you refuse?” | exclusions, ESG, leverage, etc. → **optimization constraints** |

Internal rule: **σ\* = min(σ\*_tolerance, σ\*_capacity)**—we never propose more risk than the client can bear, even if they want more. The result is then mapped to a stable client-facing risk category; the continuous value remains available only for calibration and technical audit.

### 3.1 The bank of 60 questions

| Block | No. | Type | Adaptive? | Asked per client |
|---|---|---|---|---|
| **A. Capacity & circumstances** | 10 | closed choice | no (fixed core) | 4 |
| **B. Psychometric tolerance** | 20 | ordered scale (4–5 options) | **yes** | 3–4 |
| **C. Swipes (choice between 2 portfolios)** | 24 | binary A/B | **yes** | 5–6 |
| **D. Constraints & preferences** | 6 | choice / multiple choice | conditional (branching) | 1–2 |
| **Total** | **60** | | | **15** |

Storage format: `questions/bank.json`, one entry per question:
```json
{
  "id": "C07",
  "bloc": "C",
  "type": "swipe",
  "texte": "Which do you prefer?",
  "options": {"A": {"mu": 0.045, "sigma": 0.06}, "B": {"mu": 0.075, "sigma": 0.14}},
  "params": {"phi_seuil": 3.66},
  "condition": null
}
```

**Block A — Capacity (10)**—examples: investment horizon; share of wealth invested; emergency savings (in months of expenses); need to withdraw money within 2 years; income stability; **maximum tolerable loss over 1 year, in %**; objective (preservation / growth / high return); market experience; knowledge of products (equities, bonds, ETFs); age bracket. → The 4 fixed-core items: **horizon, maximum loss, liquidity needs, experience**.

**Block B — Psychometric tolerance (20)**—scenario questions, each with options ordered from most cautious to most daring. Examples:
- “Your portfolio loses 20% in one month. You: sell everything / sell some / do nothing / buy more.”
- “You have won CHF 1,000. You prefer: keep it / a 50% chance of CHF 2,000 / a 20% chance of CHF 5,000.”
- “Your friends describe you as: very cautious / cautious / willing to take risks / a gambler.”
- “When you think of the word ‘risk,’ you first think of: loss / uncertainty / opportunity / thrill.”
Draw inspiration from scales validated in the literature (e.g., Grable & Lytton, 1999)—**do not copy**; rephrase and adapt them.

**Block C — Swipes (24)**—the “Tinder” element. Each pair compares a **conservative** portfolio (μ_A, σ_A) with a **bold** one (μ_B, σ_B), presented in concrete terms (1-year range, loss during a historical crisis, average gain). **Design insight:** with mean-variance utility U = μ − (φ/2)σ², the client is **indifferent** between A and B when

$$\varphi_{\text{seuil}} = \frac{2(\mu_B - \mu_A)}{\sigma_B^2 - \sigma_A^2}$$

A client with φ > φ_seuil chooses A (conservative), otherwise B. Each pair is therefore a “step” on the φ scale. We **construct the 24 pairs** so that their φ_seuil values are **distributed on a logarithmic grid** from 0.5 to 20 → allowing us to locate any client.

**Block D — Constraints (6)**—sector exclusions (e.g., fossil fuels), refusal to hold gold, maximum weight per asset, whether leverage is permitted, ESG preference, desired rebalancing frequency. **Conditional** questions: ask “which sectors should be excluded?” only if the client answered “yes, I have exclusions.”

### 3.2 Response model (how each answer informs φ)

We work with **θ = log φ** (a more symmetric scale). Each question type has a **likelihood** P(response | θ):

- **Swipe (Block C)**—logit of the utility difference:
  $$P(\text{choose B}\mid\varphi) = \frac{1}{1+\exp\!\big(-\lambda\,[U_B(\varphi) - U_A(\varphi)]\big)}$$
  λ = response sharpness (noise): estimated or fixed, then sensitivity-tested.
- **Ordered scale (Block B)**—graded response model (IRT) / ordered logit:
  $$P(\text{response} \geq k \mid \theta) = \frac{1}{1+\exp(-a\,(b_k - \theta))}$$
  a = the question's discrimination parameter; b_k = option thresholds. (Sign: a bold response indicates a **low** θ, i.e., low aversion.) Parameters are set **a priori** by the group, then **recalibrated** if the survey is conducted (3.10).
- **Block A:** does not enter the likelihood for φ (it measures capacity)—except “maximum loss,” which can be used **both** as a capacity measure and as a weakly informative item.

### 3.3 Bayesian engine
- **Prior** on θ: a 200-point grid over [log 0.3, log 30], with a sufficiently broad normal prior centered on “average” aversion (e.g., φ ≈ 3).
- After each response: **posterior ∝ prior × likelihood** (pointwise multiplication over the grid, then normalization).
- Estimators: posterior mean / median of θ, **posterior standard deviation** (= our precision measure), and an 80% credible interval.

### 3.4 Adaptive selection of the next question
At each step, among questions **not yet asked** and **eligible** (conditions, quotas by block):
- calculate each candidate question's **expected posterior variance** after its response (average across possible responses, weighted by their predictive probability);
- ask the question that **minimizes** this variance (= maximizes expected information).

Intuition: like a **binary search**—ask the pair whose φ_seuil is close to the current estimate. For swipes, this is very close to “choose φ_seuil ≈ posterior median.”

**Quotas** to maintain a varied experience: typical order = 4 Block A questions (fixed core) → adaptive alternation between B / C → 1–2 Block D questions at the end.

### 3.5 Stopping rule
Stop when the **posterior standard deviation of θ < threshold** (e.g., 0.20) **or** 15 questions have been reached. Display the achieved precision.

### 3.6 Consistency check
- 1 “mirror” Block C question (same φ_seuil, different presentation). If the answer contradicts the first → a playful message (“are you swiping at random? 👀”) and a lower λ (noisier responses → wider interval).
- Detect tolerance/capacity contradictions (e.g., wants substantial risk but horizon < 2 years) → explanatory message.

### 3.7 Capacity → σ*_capacity (explicit rules)
- **Maximum loss L** (1 year, in %): using a 95% Gaussian approximation, loss ≈ 1.645·σ − μ, therefore
  $$\sigma^*_{\text{cap}} \approx \frac{L + \mu_{\text{port}}}{1.645}$$
- **Horizon:** caps by bracket (e.g., < 2 years → σ ≤ 5%; 2–5 years → σ ≤ 10%; > 5 years → no cap). Values must be **justified** in the documentation.
- **Liquidity:** imminent withdrawal need → additional cap.
- σ*_capacity = minimum across all rules.

### 3.8 Tolerance → σ*_tolerance (link to the course)
With a risk-free asset, the client invests the fraction w = (μ_T − r)/(φ σ_T²) in the tangency portfolio (Tobin, LN1), so their volatility is

$$\sigma^*_{\text{tol}} = w\,\sigma_T = \frac{SR_T}{\varphi}$$

where SR_T = reference Sharpe ratio (Step 2.4). A simple and highly pitchable result.
**σ\* = min(σ\*_tol, σ\*_cap)**, with an uncertainty band derived from the posterior of φ.

### 3.8b Continuous estimate → client risk category

The application does not present σ* as a precise promise. It assigns one of four prepared categories:

| Category | Volatility band | Reference used for prepared portfolios |
|---|---:|---:|
| Conservative | 4%–6% | 5% |
| Balanced | 6%–9% | 8% |
| Growth | 9%–12% | 10% |
| Aggressive | 12%–15% | 14% |

The lower bound is inclusive and the upper bound is exclusive, except for the final band. If tolerance and capacity imply different categories, the more conservative permitted category wins. The client sees the category, its range, and a plain-language explanation; the technical panel retains φ, σ*_tol, σ*_cap, the reference volatility, and the achieved volatility.

### 3.9 Precision validation (essential—our primary argument)
**Synthetic client simulation:**
1. Draw 1,000 “true” φ values (log-uniform over [0.5, 20]).
2. Simulate their responses using the model in 3.2 (with noise λ).
3. Administer the **adaptive** questionnaire and compare it with: (a) 15 **random** questions, (b) 15 **fixed** questions, and (c) all **60** questions.
4. Measure: **RMSE** on log φ, **error in σ*** (in volatility percentage points), and **% of clients assigned to the correct risk category**, as a function of the number of questions.
5. Robustness tests: greater noise (low λ), misspecified item parameters.

Deliverable: “error vs. number of questions” curve (adaptive vs. random) → **the key figure in the pitch**.

### 3.10 (Optional) Calibration using a real survey
Administer all 60 questions to approximately 40–60 students (Google Forms) → estimate parameters a and b_k for Block B items and λ for swipes; remove questions with low discrimination; verify internal consistency (Cronbach's alpha) and the correlation between Blocks B and C. A major credibility bonus.

### 3.11 Profiling output
A `profile` object (JSON):
```json
{"phi_median": 3.4, "phi_ci80": [2.6, 4.5], "sigma_star_internal": 0.103,
 "sigma_tol": 0.103, "sigma_cap": 0.12, "risk_band": "growth",
 "risk_band_range": [0.09, 0.12], "reference_volatility": 0.10,
 "precision_sd_theta": 0.18,
 "constraints": {"exclusions": ["XLE"], "leverage": false, "w_max": 0.30},
 "answers": [...]}
```

---

## Step 4 — Signals: sentiment, Fed, and regimes

### 4.1 Sector polarity (StockTwits, LN7)
- Firm-day polarity: P = (Nbull − Nbear)/(Nbull + Nbear).
- First reproduce the LN7 method: market polarity, abnormal volume, events, and **abnormal polarity as the residual from a market model**. A simple difference from a moving average must not be called “abnormal” in the course's sense.
- Then test sector aggregation and monthly frequency as a separate hypothesis. LN7 warns that raw polarity is primarily contemporaneous; only out-of-sample validation can justify its predictive use.
- Because the course data end in 2020, the sentiment portfolio remains a **historical case study** until a current, publishable source is validated. The app must not display a fake “live” view.

### 4.2 Fed tone (FOMC)—extension
- Classify each sentence in statements with FOMC-RoBERTa (hawkish / dovish / neutral) **offline**.
- Tone index per document: (no. hawkish − no. dovish)/total no. Associate it with the **publication date**.

### 4.3 Constructing Black-Litterman views (P, Q, Ω)
- **Candidate sentiment view** (relative): “sector with the strongest abnormal signal − sector with the weakest” → row of P with +1 / −1, only if the Step 4.1 test is conclusive.
- **Fed view** (relative): hawkish tone → negative “long-term bonds (TLT) − equities,” etc.
- **Q:** magnitude estimated by an event study / prespecified historical regression, **using past data only**. If the effect is unstable, Q = 0 or the view is disabled.
- **Ω:** documented and tested confidence rule. Volume may be used; classifier confidence may be used only if it genuinely exists in the supplied data. Weak or uncertain signal ⇒ large Ω ⇒ low-impact view.

### 4.4 Macro regimes (HMM)—extension
- Model: `hmmlearn.hmm.GaussianHMM`, 3 or 4 states, using the standardized variables from 1.3.
- **Expanding-window estimation:** at each rebalancing date, use only past data. Use **filtered probabilities** (not smoothed probabilities—the latter use future data).
- Label regimes after estimation (☀️ calm expansion, ⛅ slowdown, ⛈️ crisis) by examining their characteristics.
- Select the number of states using BIC + interpretability.

---

## Step 5 — Portfolio construction

**Principle:** each strategy produces a **risky core** x_risky (long-only, sum = 1). The prepared client portfolio uses a **Tobin allocation** between this core and cash to reach the assigned category's reference volatility (5.6).

### 5.0 Shared functions (`src/optim.py`)
`port_vol(x, Σ)`, `risk_contrib(x, Σ)` (RC and RC*, LN5), `tracking_error(x, x_b, Σ)` (LN2), `markowitz_qp(...)`, `erc(Σ)` (log barrier + rescaling, LN5 lab), `risk_budget(Σ, b)`, `bl_posterior(...)` (LN4 lab), `target_vol(...)` (LN1 lab). **Start from the completed labs.**

### 5.1 🏛️ The Classic—constrained Markowitz (LN1, LN3)
- Input: Ledoit-Wolf Σ, conservative μ (2.3).
- Core: **long-only tangency** portfolio (maximum Sharpe) with constraints: 0 ≤ x_i ≤ 30%, asset classes (e.g., equities ≤ 80%).
- Control: show instability when shrinkage + constraints are removed (composition maps, LN3 lab).

### 5.2 ⚖️ The Balanced—ERC (LN5)
- Input: Σ only (no μ!).
- Core: ERC using a log barrier + rescaling. Verify RC*_i = 1/n.

### 5.3 🧠 The Connected—Black-Litterman (LN4)
1. x0 = explicit reference portfolio. ERC may serve as a neutral anchor, but it must not be presented as the market portfolio; compare it with 60/40 or available market weights.
2. Implied φ via target Sharpe: φ = SR/σ(x0); μ̃ = r + φ Σ x0.
3. Views P, Q, Ω from Step 4.3 (if no view is available → μ̄ = μ̃).
4. Γ = τΣ, μ̄ = μ̃ + ΓPᵀ(PΓPᵀ + Ω)⁻¹(Q − Pμ̃).
5. Core = long-only tangency portfolio using μ̄.
6. τ calibrated to a **target tracking error** vs. x0 (e.g., 3%), as in the LN4 lab.
- Available over the sentiment period (2010–2020); outside it, only the Fed view is available.

### 5.4 🌦️ The Chameleon—risk budgeting by regime (LN5, LN6)
- For each regime k: risk budgets b(k) by asset group (e.g., ☀️ equities 70% / bonds 20% / gold 10%; ⛈️ equities 30% / bonds 45% / gold 25%—**assumptions to justify**).
- Effective budgets = Σ_k P(regime k | past data) · b(k) (filtered probabilities).
- Core = risk budgeting using Σ (option: regime-specific Σ, or ES instead of volatility—LN6).

### 5.5 📈 The Benchmark
60% SPY / 40% IEF, scaled to each category reference through allocation to cash. Serves as the reference for TE and the information ratio.

### 5.6 Prepared portfolios by risk category
- Offline, build one catalogue entry for every validated `risk band × strategy` pair.
- Without personal constraints: x_client = (σ_ref/σ_risky) · x_risky + (1 − σ_ref/σ_risky) · cash, where σ_ref is the category reference volatility.
- **Leverage:** if σ_ref > σ_risky → cap at 100% invested by default. Any leveraged variant must be explicitly approved and labelled.
- **Personal constraints** (exclusions, maximum weights): Tobin separation no longer holds → **re-optimize** the core with the constraints (fast: < 1 s).
- Store the category range, reference volatility, achieved volatility, weights, metrics, data date, comparison period, and configuration version.

### 5.7 Analytics by portfolio (displayed in the app)
Weights · RC and RC* (“X% of your money = Y% of your risk”) · ex-ante volatility · TE and IR vs. benchmark · concentration indices (Herfindahl, LN6) · current regime and active views (Connected, Chameleon).

---

## Step 6 — Backtesting

### 6.1 Engine
- Loop over month-ends. At each date t: estimate Σ (3-year rolling window), signals (past data only), cores of active strategies, and allocations for the four category references.
- Hold the portfolio until t+1 month; weights **drift** with prices between rebalancing dates.
- Cash return = DTB3.

### 6.2 Prepared risk-band catalogue
Run the four reference targets `{5%, 8%, 10%, 14%}` × active strategies, corresponding to Conservative, Balanced, Growth, and Aggressive. Thanks to Tobin separation, one risky core per strategy is sufficient in the unconstrained case; only the risky/cash allocation changes. The Chameleon enters the catalogue only if it meets the extension criteria.

### 6.3 Transaction costs (LN3)
Cost = c × turnover, with c = 10 bps by default (**assumption**, sensitivity at 0 / 10 / 25 bps). Turnover = Σ|x_new − x_drifted|.

### 6.4 Metrics
- **Realized volatility vs. category reference and range** ← the test that validates the chain from profile to prepared portfolio.
- Historical annualized return, Sharpe, Sortino, maximum drawdown, Calmar.
- Average turnover, total costs.
- TE and information ratio vs. benchmark.
- Performance **by regime** (Chameleon vs. others during ⛈️).

The five client-facing measures are: **historical annualized return net of costs, realized volatility, net Sharpe ratio, maximum drawdown, and annualized cost**. Sortino, Calmar, Expected Shortfall, turnover, concentration, TE, IR, and risk contributions appear under “Technical details.” Historical return is never labelled as a forecast.

### 6.5 Robustness
Estimation window (2 / 3 / 5 years), frequency (monthly / quarterly), costs, subperiods (2009–2014, 2015–2019, 2020–present), with / without shrinkage.

### 6.6 Export
`results/backtests.parquet` (value series), `results/metrics.parquet`, `results/weights_history.parquet`, and `results/portfolio_catalogue.parquet` → read by the app. The catalogue contains one dated, versioned row per `risk_band × strategy`, using the same comparison period and net-of-cost results first.

---

## Step 7 — Client selection and monitoring

### 7.1 Selection
The client compares the available strategy cards within their assigned risk category and selects one. Every card uses the same reference risk and common historical period. It presents five primary measures plus short, evidence-based advantages and limitations. Record: profile, category, strategy, catalogue version, historical metrics shown, date, initial prices, initial weights, and amount.

### 7.2 Monte Carlo projection
- Simulate 10,000 wealth paths over the client's horizon (returns drawn from a multivariate normal distribution using conservative μ and Σ, or a **block bootstrap** of historical returns—more realistic).
- Display the range (5th / 50th / 95th percentiles) and the **probability of reaching the objective** (Block A).

### 7.3 Portfolio monitoring
Because we do not have real accounts, there are two modes:
- **Historical mode** (“what if you had invested on January 1, 2020?”): replay monitoring using historical data.
- **Live mode:** update using the latest yfinance prices (“refresh” button).

Monitored elements: value and return **since selection**, performance vs. benchmark, **weight drift** vs. target, current drawdown, and rolling realized volatility vs. the selected category range. Historical backtest evidence remains frozen and visually separate from live performance.

### 7.4 Rebalancing rules and alerts
- **Calendar-based** rebalancing (monthly / quarterly, selected by the client) **and/or threshold-based** rebalancing (a weight deviates by more than ±5 percentage points from its target).
- Alerts: realized volatility above the category ceiling; regime change (Chameleon); drawdown above the declared maximum loss; new strong view (Connected); or weights drifting beyond the chosen threshold.

### 7.5 Reassessment
Offer a **short** questionnaire (5 adaptive questions, using the previous posterior as the prior) every 12 months or after a life event / major drawdown.

### 7.6 Client report
“Download my report” button (PDF or HTML): profile, portfolio, performance, and next steps.

### 7.7 Persistence
Streamlit Community Cloud **does not provide reliable persistent storage**. Simple solution: the client downloads their profile/portfolio as **JSON** and can upload it again later. Advanced option: a free external database (e.g., Google Sheets / Supabase)—not required for the grade.

---

## Step 8 — The Streamlit web app

### 8.1 Multipage structure
```
app/
├── Home.py                 # home + three-line pitch + “Start” button
├── pages/
│   ├── 1_🎯_Profile.py      # fixed MVP profile, adaptive later
│   ├── 2_🍽️_Portfolios.py   # simple cards within the assigned risk category
│   ├── 3_🔍_Analysis.py     # optional technical evidence and methodology
│   └── 4_📡_Monitoring.py   # since-selection results, drift and rebalance alerts
└── components/             # reusable cards and charts
```

### 8.2 Session state
`st.session_state` contains: `posterior`, `questions_asked`, `answers`, `profile`, `selection`, `portfolio`. One question at a time: click → update posterior → `st.rerun()`.

### 8.3 Page content
- **Profile:** one question at a time; at the end reveal the named category, range, capacity explanation, and constraints. Keep φ and precise calibration in “Technical details.”
- **Portfolios:** one card per validated strategy at the category reference risk. Show historical net annualized return, realized volatility, net Sharpe, maximum drawdown, annualized cost, and concise pros/cons.
- **Analysis:** optional weights, risk contributions, Sortino, Calmar, Expected Shortfall, turnover, concentration, views, common-period walk-forward evidence, and Monte Carlo only if validated.
- **Monitoring:** value and performance since selection, benchmark, current drawdown, weight drift, risk-band status, alerts, rebalance button, reassessment, and JSON/report export.

### 8.4 Performance
- `@st.cache_data` to load result files; `@st.cache_resource` for heavy objects.
- **No** compute-intensive online operations: HMM, NLP, backtests = precomputed. Online: Bayesian engine (instantaneous), Tobin allocation, constrained re-optimization (< 1 s).
- Plotly charts (`st.plotly_chart`).

### 8.5 Design
Consistent palette, emojis for the 5 characters, short jargon-free client-facing text, and a collapsible “technical details” mode (`st.expander`) for the instructor.

### 8.6 Tests
- Unit tests (`pytest`): RC sum to σ (Euler), ERC has equal RC, BL without views → μ̄ = μ̃, posterior is normalized, category boundaries are deterministic, capacity caps tolerance, and Tobin allocation produces the category reference risk.
- **End-to-end** test: 20 simulated profiles pass through the entire app without errors.
- Test on a computer other than the developer's.

### 8.7 Deployment
1. Clean `requirements.txt` (pin versions with `pip freeze > requirements.txt`, then clean it up).
2. Public GitHub repository.
3. Streamlit Community Cloud → “New app” → repository + `app/Home.py`.
4. Make the app public. Test the link on a phone.

---

## Step 9 — The pitch

15-minute storyline:
1. **The problem** (1 min): “no one knows their risk level; bank questionnaires are long and imprecise.”
2. **Live demo** (5 min): the instructor answers the questionnaire → profile → menu → analysis → monitoring.
3. **Under the hood** (5 min): QARM tools (Markowitz, ERC, BL), mapping to the risk target, and walk-forward validation. If the adaptive approach is genuinely validated, then show its precision curve against the fixed baseline.
4. **Honest limitations** (2 min): stated preferences, fragile sentiment signal, sentiment data only through 2020.
5. **Q&A** (2 min)—prepare for challenging questions: “why 15 questions?”, “how do you calibrate Ω / τ?”, “what if the client lies?”, “why use ERC as x0?”, “look-ahead in the HMM?”

---

## Repository structure

```
riskmatch/
├── README.md                  # this document
├── CHECKLIST.md               # task checklist
├── RiskMatch_pipeline.ipynb   # step-by-step execution (same numbering)
├── Makefile                   # install, test, app, and check commands
├── requirements.txt
├── config.yaml                # tickers, dates, SEED, assumptions (SR, costs, thresholds)
├── docs/                      # framework, course, methodology, plan, and decisions
├── .github/                   # CI, issue template, and pull request template
├── data/
│   ├── raw/  processed/
│   └── README_data.md
├── questions/
│   └── bank.json              # 60 questions + parameters
├── src/
│   ├── data_loader.py         # Step 1
│   ├── estimation.py          # Step 2
│   ├── questionnaire.py       # Step 3 (Bayesian engine, selection, stopping)
│   ├── profiling.py           # Steps 3.7–3.8 (capacity, φ → category)
│   ├── signals.py             # Step 4 (StockTwits; FOMC/HMM as extensions)
│   ├── optim.py               # Step 5 (shared functions + active strategies)
│   ├── backtest.py            # Step 6
│   └── monitoring.py          # Step 7
├── results/                   # precomputed outputs read by the app
├── app/                       # Step 8
└── tests/
```

---

## Role allocation

| # | Role | Steps |
|---|---|---|
| 1 | **Client & profiling** | 3 + user testing + integration of capacity/constraints |
| 2 | **Data & signals** | 1, 4 |
| 3 | **Optimization** | 2, 5 (starting from the labs) |
| 4 | **Backtesting & monitoring** | 6, 7 |
| 5 | **App, integration & pitch** | 8, 9, 10 + integration of everything |

Team rule: every function in `src/` has a test, and every PR is reviewed by another person.

---

## Pitfalls to avoid

1. **Look-ahead bias:** rolling estimation only; **filtered** HMM probabilities; macro data lagged by their publication delay; Q for views estimated from past data.
2. **γ / φ confusion:** in the course, γ = tolerance and φ = aversion. The questionnaire estimates **φ**.
3. **Raw μ:** never feed the raw historical mean into Markowitz (LN3).
4. **Squaring Ω:** when reasoning in terms of standard deviations ϖ, Ω = diag(ϖ²) (LN4 pitfall).
5. **ERC:** remember to **renormalize** after the log barrier (LN5).
6. **Survivorship:** the selected ETFs exist over the entire period—do not add recent ETFs without disclosing it.
7. **Currency:** everything is in USD; a Swiss client bears exchange-rate risk. Mention this (or provide a CHF option using `USDCHF=X`).
8. **App:** no compute-intensive online operations; test deployment **early**.
9. **Licenses:** FOMC-RoBERTa is CC BY-NC (noncommercial use)—cite the source.

---

## References

- Divernois, M.-A. — QARM II, “Projects” slides, lecture notes LN1–LN7, and labs, HEC Lausanne.
- Divernois, M.-A. & Filipović, D. (2022). StockTwits classified sentiment and stock returns. *Digital Finance*.
- Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*.
- Black, F. & Litterman, R. (1992). Global Portfolio Optimization. *Financial Analysts Journal*.
- Ledoit, O. & Wolf, M. (2004). Honey, I Shrunk the Sample Covariance Matrix. *Journal of Portfolio Management*.
- Maillard, S., Roncalli, T. & Teïletche, J. (2010). The Properties of Equally Weighted Risk Contribution Portfolios. *Journal of Portfolio Management*.
- Grable, J. & Lytton, R. H. (1999). Financial risk tolerance revisited: the development of a risk assessment instrument. *Financial Services Review*.
- Samejima, F. (1969). Estimation of latent ability using a response pattern of graded scores. *Psychometrika Monograph Supplement*.
- Shah, A., Paturi, S. & Chava, S. (2023). Trillion Dollar Words: A New Financial Dataset, Task & Market Analysis. *ACL 2023*. Model: `huggingface.co/gtfintechlab/FOMC-RoBERTa`.
- Hamilton, J. D. (1989). A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle. *Econometrica*.
