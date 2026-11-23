# RiskMatch client studio

![Cherry and title rising over the Miami lagoon](entrance.jpg)

The entry scene leads to one investment brief, an adaptive card deck, a behavioural profile, the asset library and a portfolio shortlist. Confirming a draft opens a private fictional CHF account. The two supported entry points run the same frontend and Python engine.

After the title sequence the lagoon stays behind the studio. The form, cards and library use translucent navy surfaces. [Desktop capture](glass-desktop.jpg) · [Mobile capture](glass-mobile.jpg)

## Open the studio

From the repository root with Python 3.12, install the application and launch the local server.

```sh
python -m pip install -e '.[catalogue,faisabilite,questionnaire]'
python -m riskmatch_v2.studio --port 8766
```

Open [the client studio](http://127.0.0.1:8766/). Streamlit users can run `python -m streamlit run app/questionnaire.py`. The archived section 13 walkthrough is available at `?view=research` on the Streamlit service.

## Named local saves

After the title, choose **New save**, enter a name and confirm a four-digit code twice. The selector lists save names on this installation. Unlock a save to resume its brief, calibration or portfolio. **Lock save** returns to the selector, and reloading requires the code again. A legacy dossier from the same browser can be imported into a new named save.

The local save registry stores salted PIN hashes and applies a five-minute delay after five failed attempts. This is a shared local simulation. Give saves fictional names. The selector shows names; dossier contents require unlocking.

## Sound and navigation

The lagoon starts a quiet original 16-bar jazz instrumental on arrival when the browser permits audible autoplay. When the browser requires a gesture, normal interaction automatically retries playback with sound enabled by default. **Press to start** triggers the title sequence. The score runs at 91 BPM, with electric piano, bass, a reed melody and brushed percussion. A splash accompanies the cherry and two soft impacts land with the title. The music loops through the studio. The speaker button on the intro and in the header remembers the mute setting. The app keeps the loop running across navigation, swipes and tab visibility changes. The browser or operating system can suspend media. Reduced motion skips the timed title effects.

The brief scrolls inside the studio in both the standalone and Streamlit entry points. [Mouse, touch and sound replay](interaction-check.json)

A right vote plays a two-note chime and a left vote plays a dry clap over the continuing music. Each left or right vote dismisses the card, bounces the cherry logo and reveals the next card or the result. The reduced-motion setting shows a still cherry. [Watch a recorded swipe](cherry-swipe.webp)

## From the first swipe to a match

| Stage | What the client sees | How it works |
|---|---|---|
| Entrance | A waterfront, a single start prompt, the rising cherry and the two falling halves of the title. | Enter, tap or click. Loading waits for the server. Reduced motion uses a short transition. |
| Brief | Five required fields cover the starting budget, cash set aside, affordable loss, target amount and target date. Each field has a short help bubble. | Optional preferences hold the savings rate, desired investment return and exclusions. Saved profiles with a planned expense can still edit or clear it. |
| Calibration | First-person propositions, heart, cross, unsure and back. | Up to 26 possible behavioural cards across seven research families. The active route changes with earlier answers. The client can revisit answers. |
| Profile | An inferred range, domain scores, reactions to loss, flexibility, framing and monitoring preferences. | Stated willingness, choices between certain and risky amounts, and willingness to hold through discomfort each contribute equally if interpretable. Comprehension, at least two choices, consistent gamble bounds and at least two interpretable domains are required. The range describes the investable sleeve. |
| Library | A searchable catalogue and charts for 3,902 instruments. | 1/3/5/10-year historical metrics, Pearson/Spearman references, macro sensitivity with intervals, historical crises, individual signals and environmental or bond fields when available. The date and missing data appear on the sheet. [Coverage](library-coverage.json) |
| Contenders | Swipe or tab through portfolios, compare risk, modeled return, fee, score, scenarios and five separate signal readings. | Each calculation uses the client's facts and the eligible universe of 3,322. The last step checks whole positions, exposure limits, loss capacity and cash. An unavailable strategy shows its reason. |
| Match | Keep one or more, choose percentages or request a suggested mix, review and confirm. | The suggested mix maximises estimated net return per unit of volatility on a positive 10% grid. The combined holdings and cost are recalculated. [Allocation method](ALLOCATION.md) |
| Follow-up | Positions, CHF value, flow-neutral return, drawdown, strategy shares, cash flows and a chart of simulated closes. | Opening costs affect the account. A deposit changes its balance and is excluded from investment performance. Later strategies are calculated from existing holdings and available cash. |

### CHF reserve and strategy split

The cash reserve stays outside the investment portfolio. Optional preferences accept an annual CHF savings rate shown on the user's account. A blank rate assumes 0%. The projection compounds that rate from the research close to the goal date and deducts planned spending on its date. It shows nominal CHF and assumes a constant rate. The goal incorporates the projected reserve separately from portfolio returns.

The investment budget is allocated at the final match. The blend screen shows shares and their CHF equivalents before charges and whole-position rounding. It applies the mandate to the combined portfolio before confirmation.

[French questionnaire study](ETUDE_QUESTIONNAIRE_FR.md) documents every proposition, its routing rule and the effect of each answer.

### Reading a behavioural score

| Willingness | Profile | Model band for annual volatility |
|---|---|---|
| 0–19 | Very cautious | 0–4% |
| 20–39 | Cautious | 4–8% |
| 40–59 | Moderate | 8–12% |
| 60–79 | Growth-oriented | 12–20% |
| 80–100 | Aggressive | 20% and above |

These thresholds are a theoretical design policy. They have not been validated with participants. A changed declaration with unknown direction contributes no stated-comfort score. Equivalent framing pairs and monitoring frequency help interpret answers. They receive no additional risk points. Zero affordable loss restricts the proposals to cash even if behavioural willingness is high. Model volatility and tested scenario losses cannot bound future losses.

## Prices and live monitoring

The checked-in model uses the research close of **30 October 2026**. Booking and replay use synthetic CHF execution marks through **5 November 2026**. The environmental review and signal evaluations are dated **23 November 2026**. Signal transfer to a custom portfolio has zero recommendation weight. No provider of live prices is connected in this release.

An operator with display rights can set `RISKMATCH_LIVE_MARKS` to an independently updated local JSON file. Use an atomic rename to publish each update. The example below illustrates the expected fields with fictitious values. The operator must provide a quote for every held symbol in the actual ledger unit (USD 100 face for a Treasury lot). The code verifies positive values, USD units, the provider's explicit display declaration, the exchange session and a maximum age of 90 seconds for every security and USD/CHF. During a visible session the app requests a fresh valuation every 15 seconds. The live valuation panel reports its oldest contributing timestamp, charts up to 240 distinct successive live marks and shows the change across the displayed observations. The historical chart and transaction ledger continue to use the dated simulation.

```json
{"source":"Example operator feed","display_authorized":true,"mode":"realtime",
 "usd_chf":{"at":"2026-11-23T15:30:00Z","value":0.90},
 "securities":{"SPY":{"currency":"USD","unit":"ledger_unit","at":"2026-11-23T15:30:00Z","value":50}}}
```

## Verification and screenshots

A fictional client kept CHF 15,000 from CHF 50,000 and answered 22 active cards. The score was 44/100, with 100 for stated comfort, 33 for risky choices and 0 for holding through discomfort. On both screen sizes the browser opened GLD, kept two strategies, checked manual and model weights, confirmed the account, advanced a close, recorded a CHF 100 deposit and reopened the saved profile. [Browser receipt](browser-check.json) · [Phone entrance](entrance-mobile.jpg) · [Profile](profile.jpg) · [Asset sheet](asset.jpg) · [Strategy](contender.jpg) · [Account](account.jpg)

```sh
python -m unittest discover -s tests
python tests/studio_browser.py
```

The browser replay uses Playwright and installed Chrome. Dossiers are isolated under the ignored local account directory. The portable library contains calculated statistics and the model contains fitted parameters. Rebuilding them from original histories requires the local research inputs. [Source register](../14-delivery/DATA.md)
