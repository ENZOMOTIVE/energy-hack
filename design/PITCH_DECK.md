# Gauntlet | Pitch Deck Build Spec

This file is the complete instruction set for building the Gauntlet pitch deck as a slide presentation (PowerPoint, Keynote, Google Slides, Gamma, or python-pptx). Every slide below gives the layout, the exact copy, the visual, the data, the speaker note, and the brand application. Build it literally.

- **Format:** 16:9, 1920 x 1080.
- **Design system:** [CORPORATE_DESIGN.md](CORPORATE_DESIGN.md). Colors and fonts are repeated inline below so this file is self-contained.
- **Structure:** an 8-slide CORE deck timed to roughly 3 minutes (lightning, demo-forward, built to win the Munich hackathon), followed by an INVESTOR APPENDIX that turns the same file into a seed deck.
- **Rule of the core deck:** one idea per slide, one number per slide. If a core slide has two messages, split it or cut one.

## Design quick reference (apply to every slide)

```
COLORS
ink      #0B0F14  (background)     panel  #121821  (cards)     line  #1F2A37 (borders)
text     #E6EDF3  (headlines/body) muted  #8B98A5  (captions)
primary  #2F81F7  (trust, benchmark line)
corona   #FFB020  (energy, eclipse, the hero accent)   corona-hot #FF8A00
recover  #2EA043  (recovered/pass)   fault  #F85149  (loss/fail)
hero gradient: #FF8A00 -> #FFD166 @135deg  (title + score reveals only)

FONTS
Headlines: Space Grotesk (700 for titles, 500 for subheads)
Body:      Inter (400/500)
NUMBERS:   JetBrains Mono  (every score, %, EUR, GW, P10, date)

LAYOUT
Background ink on every slide. One accent per slide. Amber is precious.
Eyebrow label top-left, all caps, muted, letter-spacing +6%, 13px.
Source/footnote bottom-left, muted, 12px.
Recovery Curve watermark allowed faint on section breaks.
```

## Per-slide template (legend for each block below)

- **Goal** | the single job of the slide.
- **Layout** | where things sit.
- **Eyebrow / Headline / Body** | the exact words. Copy verbatim.
- **Visual** | what to draw or place.
- **Data** | the number that anchors the slide.
- **Notes** | speaker script, timed. The core notes together run about 3 minutes.
- **Design** | background and accent for this slide.

---

# CORE DECK (8 slides, ~3 minutes)

---

## Slide 1 | Title and hook

- **Goal:** name the category in one breath and set the dark, instrument-grade tone.
- **Layout:** centered. Logo lockup top-center. Display headline mid. One-line subhead below. Faint Recovery Curve watermark spanning the lower third.
- **Eyebrow:** GAUNTLET
- **Headline:** "The proving ground for autonomous energy agents."
- **Subhead:** "We simulate the worst day a grid can throw at an agent, and score what it recovers in euros."
- **Visual:** the logo mark (ring with the recovery notch) at hero size. Recovery Curve watermark dipping and recovering across the base.
- **Data:** none. Restraint here.
- **Notes (~15s):** "Energy companies are handing real money and real assets to autonomous agents. Nobody can prove those agents survive a bad day. Gauntlet is the proving ground that can."
- **Design:** `ink` background. Hero accent: the corona gradient on the mark only. Everything else `text` and `muted`.

---

## Slide 2 | Problem

- **Goal:** make the trust gap undeniable.
- **Layout:** left column headline and one stat in Data L; right column three short failure lines stacked.
- **Eyebrow:** THE PROBLEM
- **Headline:** "Agents ship faster than anyone can prove they are safe."
- **Body (right, stacked, each with a line icon):**
  - "Trading agents move real positions automatically."
  - "Forecasting agents call solar and wind output."
  - "O&M agents dispatch crews and curtail plants."
- **Data (left, Data L mono):** "under 50%" with caption "of enterprise AI pilots ever reach production. Trust is the number one blocker." 
- **Visual:** the three failure lines each end in a small `fault` marker. Left stat in `fault` to signal the leak.
- **Notes (~25s):** "Across enterprise AI, fewer than half of paid pilots reach production, and the reason cited most is trust. In energy that gap is worse, because a wrong move is not a bad chatbot reply. It is a mistimed trade or a missed fault that costs real euros. Today validation is a six to twelve month manual slog, or hope-and-pray deployment."
- **Design:** `ink`. Accent `fault`.

---

## Slide 3 | Why now

- **Goal:** create urgency with a dated, physical event the audience already half-knows.
- **Layout:** full-bleed eclipse disc on the right (the mark blown up, corona gradient). Left: headline plus two stacked stats in mono.
- **Eyebrow:** WHY NOW
- **Headline:** "The grid's next stress test has a date."
- **Body:** "12 August 2026: a total solar eclipse crosses northern Spain and dims solar across Europe into the evening price ramp. The 2027 eclipse is bigger."
- **Data (two mono stats):**
  - "4.5x" caption "more EU solar than the 2015 eclipse, when Europe lost 17 GW and reintegrated 25 GW at three times the normal ramp."
  - "406 GW -> 671 GW" caption "EU solar today to 2028. More autonomy, more exposure, every year."
- **Visual:** eclipse disc with corona gradient ring on the right half. A faint map of the totality path (Bilbao, Zaragoza, Valencia) optional.
- **Notes (~25s):** "This is not hypothetical. On the twelfth of August an eclipse dims European solar right as the evening peak ramps. In 2015 the grid passed that test with 90 gigawatts of solar. We now have four and a half times that, far more of it steered by agents, and a bigger eclipse follows in 2027. The bad day is on the calendar. The question is whether your agent is ready for it."
- **Design:** `ink`. Hero accent: corona gradient on the eclipse only.

---

## Slide 4 | Solution

- **Goal:** state what Gauntlet is and the wedge in one slide.
- **Layout:** centered headline; below it a single horizontal flow diagram.
- **Eyebrow:** THE SOLUTION
- **Headline:** "Gauntlet is the validation layer. We do not build agents. We certify them."
- **Flow diagram (left to right, 4 nodes connected by arrows):** `Any agent` -> `Run the gauntlet (bad-day scenarios)` -> `Score in euros (% of recoverable losses recovered)` -> `Certificate + replay`
- **Body (one line under the flow):** "Independent, physics-based, reproducible. Same agent, same day, same score, every time."
- **Data:** none, or a small "3 hand-built bad days + 30 machine-generated ones" tag.
- **Notes (~20s):** "Gauntlet is the crash-test lab for energy agents. Bring any agent. We throw realistic bad days at it, score in euros how much of the recoverable loss it actually recovered, and hand back a certificate and a replay. We are neutral. We never compete with the agent makers. We make their agents sellable."
- **Design:** `ink`. Accent `primary` on the flow line, `recover` on the final certificate node.

---

## Slide 5 | Demo (the hero moment)

- **Goal:** show the working product. This is the slide you talk over while the live demo runs.
- **Layout:** large product screenshot or live window. Caption strip beneath with three short callouts.
- **Eyebrow:** LIVE
- **Headline:** "Watch a bad day play out."
- **Callouts (under the screen, mono labels):**
  - "Inject the cloud front and the silent fault."
  - "Two agents react in real time."
  - "The euro gap is the score."
- **Visual:** the Arena / replay view with the Recovery Curve: `muted` floor, `primary` oracle, agent lines, `fault` markers where the bad events hit. If no live demo, embed a high-resolution screenshot from `make demo`.
- **Data:** the on-screen score, live.
- **Notes (~35s, talk over the demo):** "Here is the real product. I drop a cloud-front forecast bust and a silent inverter fault into the day. The rules agent panics, false-dispatches a crew, and loses money. The certified agent holds position, pre-trades the eclipse, and recovers most of the loss. The shaded band is the money that was recoverable. The score is the fraction of it the agent actually saved. This runs in seconds, deterministically, so you can replay any decision."
- **Design:** `ink`. Let the product's own colors carry it. Keep chrome minimal.

---

## Slide 6 | Proof it works

- **Goal:** prove the gym discriminates good agents from bad and finds failures on purpose. Real numbers.
- **Layout:** two stacked horizontal bars (a mini leaderboard) on top; one adversarial callout below.
- **Eyebrow:** THE PROOF
- **Headline:** "The gauntlet separates a real agent from a fragile one."
- **Data (mini leaderboard, mono, from the discrimination battery, 30 cases):**
  - "Certified agent: 55% pass, P10 10%" bar in `recover`.
  - "Rules baseline: 8% pass" bar in `corona`.
- **Adversarial callout (boxed, below):** "Point the generator at an agent and it mines the failures: mean recovery falls from 49% to 30%. We find the bad day before your customer does."
- **Visual:** two bars with mono figures and a P10 whisker on the certified bar. The adversarial box uses a small downward Recovery Curve.
- **Notes (~25s):** "And it is not a toy. On a battery of thirty machine-generated bad days, a real agent passes 55 percent with a tenth-percentile of ten. The rule-based baseline passes eight. Then we run it in adversarial mode: we point the search at one agent and hunt its weaknesses. Its average recovery drops from forty-nine to thirty percent. We surface the failure before a customer ever sees it."
- **Design:** `ink`. `recover` for the certified bar, `corona` for the baseline, `fault` accent on the adversarial box.

---

## Slide 7 | The money slide (Invertix named)

- **Goal:** the single most important slide. Show, in euros, how much Gauntlet grows an agent company.
- **Layout:** headline top. Center: a simple before/after bar pair. Right rail: the ROI line in Data L.
- **Eyebrow:** THE BUSINESS
- **Headline:** "We make agent companies more money than we charge them."
- **Before/after (mono, labeled):**
  - "Invertix pipeline: 10 GW. Without certification, 40% converts. 4.0 GW. EUR 10.0M ARR."
  - "With a Gauntlet certificate, conversion 52%. 5.2 GW. EUR 13.0M ARR."
- **Hero number (Data L, corona gradient):** "+EUR 3.0M ARR / +30%"
- **ROI line (right rail, mono):** "Our fee: 5% = EUR 650K. Their gain: EUR 3.0M. Every EUR 1 they pay returns EUR 4.6."
- **Model footer (one line):** "Three revenue paths: white-label certification, SaaS for operators, custom-scenario consulting."
- **Visual:** two bars (EUR 10.0M vs EUR 13.0M), the delta band shaded `recover` and labeled +EUR 3.0M. ROI as a 1 -> 4.6 arrow.
- **Notes (~30s):** "Here is why an agent company pays us. Invertix already monitors 1.8 gigawatts and has a ten gigawatt pipeline. Their bottleneck is not building agents. It is getting customers past the is-it-safe gate. A certificate lifts that conversion from forty to fifty-two percent. On their pipeline that is three million euros of new recurring revenue, a thirty percent lift. We charge five percent, about six hundred fifty thousand. Every euro they pay us returns four and a half. That is an easy yes."
- **Design:** `ink`. Hero accent: corona gradient on the +EUR 3.0M only. Bars in `muted` and `recover`.
- **Caveat to keep honest (small footnote):** "ARPU and conversion are labeled estimates; figures scale with the pipeline as it ramps."

---

## Slide 8 | Close: the bad day is dated

- **Goal:** leave one clean, urgent impression (the bad day is on the calendar) and a low-pressure invitation to talk. No vote, no fundraise. The audience should remember us and know how to find us.
- **Layout:** centered. Eyebrow top. The two dates large in Data L mono, side by side, with a faint eclipse disc behind them. One subhead line, one forward line, one soft invitation. Footer strip with the live demo link and team contact. Logo lockup and tagline at the base.
- **Eyebrow:** THE CLOCK
- **Headline (two dates, Data L mono):** "12 Aug 2026  /  2 Aug 2027"
- **Subhead:** "The bad day is on the calendar. The next one is bigger."
- **Forward line:** "By then, autonomous agents will be steering the grid. Gauntlet makes sure they are ready."
- **Invitation (soft, no ask):** "If you build or rely on energy agents, come find us. We will show you, in euros, what their bad day costs."
- **Footer (mono, placeholders to fill):** "Live demo: [demo URL or QR]   |   [Name] . [email or handle]"
- **Tagline (sign-off):** logo lockup above "The proving ground for autonomous energy agents."
- **Visual:** faint eclipse disc (corona gradient ring) behind the two dates. A thin Recovery Curve along the base recovering to a peak on the right, ending on an up-note.
- **Data:** the two dates.
- **Notes (~15s):** "The bad day is not hypothetical. It is on the calendar: this August, and a bigger one in 2027. By then, agents will be steering the grid. Gauntlet is the proving ground that makes sure they are ready. If you build or rely on energy agents, come talk to us. We will show you, in euros, what their bad day costs."
- **Design:** `ink`. Hero accent: corona gradient on the eclipse disc and the two dates. `recover` on the closing curve. Keep it lean, no clutter.

---

# INVESTOR APPENDIX

Use these when the deck is read by investors or shown in a longer meeting. They expand slides 6, 7, and 8. Same design system. Numbers can stay in Data M mono in denser tables.

---

## A1 | Market (TAM / SAM / SOM)

- **Eyebrow:** MARKET
- **Headline:** "Every agent-managed gigawatt is a certification surface."
- **Body (three tiers, mono figures):**
  - "TAM: ~EUR 15M/yr today, past EUR 25M/yr by 2028. 5% of agent-software revenue across EU solar (406 GW to 671 GW), as autonomy takes over asset management."
  - "SAM: EU 'AI worker for energy' vendors plus large-operator in-house agent teams (Enerparc, E.ON)."
  - "SOM (beachhead, year 1 to 2): 3 to 5 white-label accounts at EUR 0.3M to 0.7M each = EUR 1M to 3.5M ARR. Invertix alone models to ~EUR 0.65M."
- **Visual:** three concentric arcs (TAM/SAM/SOM) in `line`, `primary`, `recover`.
- **Notes:** "We capture a slice of agent revenue, and that base grows with installed capacity and with the share that becomes agent-managed. The beachhead is the handful of agent companies; we do not need the long tail to hit our first million."
- **Source footnote:** "EU solar capacity: SolarPower Europe. Agent-software share and ARPU are labeled estimates."

---

## A2 | Business model (three paths)

- **Eyebrow:** REVENUE MODEL
- **Headline:** "One product, three ways to sell it."
- **Body (three cards):**
  - "White-label certification (agent companies). 5% of certified-agent revenue, or EUR 10K per agent plus annual re-cert. The engine."
  - "SaaS (asset operators). Tiered monthly subscription to run their own agents through the gym. Starter, Professional, Enterprise."
  - "Consulting (custom scenarios). Build a bespoke failure mode for a large operator or regulator and deliver a benchmarked report."
- **Visual:** three `panel` cards, the white-label card highlighted with a `corona` top border as the primary engine.
- **Notes:** "White-label is the high-margin engine and the focus. SaaS widens the funnel. Consulting funds custom scenario R&D and opens enterprise doors."

---

## A3 | Revenue uplift, sensitivity

- **Eyebrow:** THE NUMBERS
- **Headline:** "The pitch survives pessimistic assumptions."
- **Body:** "Incremental ARR for the agent company = pipeline GW x conversion uplift x ARPU per GW. Worked on Invertix's 10 GW."
- **Data (grid, mono):**

| Conversion uplift | EUR 2.0M/GW | EUR 2.5M/GW (base) | EUR 3.0M/GW | EUR 4.0M/GW |
|---|---|---|---|---|
| +8 pp | 1.6M | 2.0M | 2.4M | 3.2M |
| +12 pp (base) | 2.4M | **3.0M** | 3.6M | 4.8M |
| +15 pp | 3.0M | 3.75M | 4.5M | 6.0M |
| +20 pp | 4.0M | 5.0M | 6.0M | 8.0M |

- **Notes:** "Even the pessimistic corner, a modest eight-point lift at low ARPU, clears 1.6 million in new ARR, comfortably above our fee. The base case is three million. Levers two through four (cycle compression, premium, churn avoidance) stack on top and are not counted here."
- **Design:** highlight the base cell `recover`.

---

## A4 | Unit economics

- **Eyebrow:** UNIT ECONOMICS
- **Headline:** "The white-label account carries the economics."
- **Data (mono list):**
  - "ARR per account ~EUR 650K. Software gross margin ~85% = ~EUR 550K gross profit."
  - "CAC (enterprise, founder-led) ~EUR 100K to 150K."
  - "Payback under 4 months. LTV:CAC roughly 12:1 to 18:1 over a 4-year life."
- **Notes:** "These are derived from the account math, not asserted. The SaaS seat is a funnel, not the engine."

---

## A5 | Go-to-market and traction

- **Eyebrow:** GO TO MARKET
- **Headline:** "Hackathon to recurring revenue in three phases."
- **Body (timeline):**
  - "Phase 1 (Sept 2026): win the hackathon, capture inbound, working MVP already built."
  - "Phase 2 (Oct to Dec 2026): outreach to 15 to 20 prospects, convert 1 to 2 paid pilots (EUR 5K to 10K)."
  - "Phase 3 (Jan to June 2027): 3 to 5 paying customers, first white-label agreement, recurring revenue."
- **Traction now:** "Working product: deterministic simulator, 3 scenarios, a 30-case machine-generated battery, real Open-Meteo and SMARD data, live LLM contestants (DeepSeek, Claude), Arena and Test Lab UIs."
- **Notes:** "The MVP exists today. The 2026 eclipse is the live demo and the 2027 eclipse is the deadline our customers feel."

---

## A6 | Competition and moat

- **Eyebrow:** WHY US
- **Headline:** "The neutral lab is the defensible position."
- **Body (compare):**
  - "Agent vendors (Invertix and peers): customers, not competitors. We make them sellable."
  - "In-house QA: slow, biased, not independent. A vendor grading its own homework does not close enterprise trust."
  - "Generic eval tools: no energy physics, no euro scoring, no bad-day library."
- **Moat:** "Real data plus a growing library of hard, discriminating scenarios plus third-party neutrality. The scenario battery compounds with every engagement."
- **Notes:** "Neutrality is the moat. The day we ship our own agent, we lose it. We will not."

---

## A7 | Team

- **Eyebrow:** TEAM
- **Headline:** "Builders across full-stack, LLM agents, and time-series ML."
- **Body (placeholder cards, fill before presenting):**
  - "[Name] | [role] | [one-line credential]"
  - "[Name] | [role] | [one-line credential]"
  - "[Name] | [role] | [one-line credential]"
- **Notes:** "Replace placeholders with real names, photos, and one credential each. If advisors or energy-domain support exist, add a small advisor row."
- **Design:** `panel` cards, mono name labels.

---

## A8 | Financials and trajectory

- **Eyebrow:** FINANCIALS
- **Headline:** "A path to recurring revenue well before the 2027 eclipse."
- **Year 1 revenue targets (mono table):**

| Timeline | Customers | ARR |
|---|---|---|
| Month 1 to 3 | 1 to 2 | EUR 30K to 60K |
| Month 4 to 6 | 3 to 5 | EUR 150K to 300K |
| Month 7 to 12 | 5 to 10 | EUR 500K to 1M |

- **Comparable:** "Invertix raised EUR 1.7M pre-seed (Vireo Ventures) for the agent layer. We are the validation layer beneath it."
- **Notes:** "Year 1 is carried by SaaS plus consulting plus the first white-label pilot. White-label is the year 2+ scaler."
- **Design:** highlight the Year 1 ARR target in corona gradient.

---

## A9 | How it works (tech deep-dive)

- **Eyebrow:** UNDER THE HOOD
- **Headline:** "Hard, discriminating bad days by construction, not random jitter."
- **Body:**
  - "Physics-based portfolio simulator (pvlib) on real and synthetic days."
  - "A test case is a genome: weather busts, optional silent fault, eclipse overlay, price regime."
  - "Evolutionary search maximizes recoverable money at stake times how far the day separates a good agent from a weak one, then diversity-selects a battery."
  - "Each case is Monte-Carlo'd: the report is pass-rate plus worst-case P10 (tail risk)."
- **Visual:** the genome -> search -> battery -> Monte Carlo pipeline as a horizontal flow.
- **Notes:** "Curation lifts mean difficulty 1.8x and good-test fraction from 42 to 83 percent versus unfiltered random. The win is the fitness function: we reward days that both put real money at stake and split the field."

---

# How to turn this file into a PPT

1. Pick a tool: PowerPoint (with Designer), Google Slides, Gamma, Beautiful.ai, or generate programmatically with `python-pptx`.
2. Set the deck to 16:9, background `#0B0F14` on every slide.
3. Install fonts: Space Grotesk, Inter, JetBrains Mono. Map headlines to Space Grotesk, body to Inter, every number to JetBrains Mono.
4. Build the 8 core slides first, in order, copying the headline and body text verbatim. Keep one number per core slide.
5. Add the appendix slides after a divider slide titled APPENDIX.
6. Apply one accent per slide per the Design line. Reserve the corona gradient for slides 1, 3, 7, 8 and A8.
7. Recreate the Recovery Curve as the recurring visual (slides 1, 5, 6, 8). Use the agent colors from CORPORATE_DESIGN.md so the demo screenshot and the drawn charts match.
8. Export speaker notes from the **Notes** blocks into the presenter-notes field.

# Fill before presenting (checklist)

- [ ] Real team names, roles, credentials (A7).
- [ ] Confirm with the organizers that naming Invertix on the money slide (slide 7) is welcome. If not, switch slide 7 to "a leading EU agent company" with the same numbers.
- [ ] High-resolution demo screenshot or a confirmed live-demo window for slide 5.
- [ ] Live demo URL or QR and a team contact (name plus email or handle) for the closing slide (slide 8).
- [ ] Re-run `make battery` and confirm the slide 6 numbers (55% / 8% / P10 10% / 49% to 30%) still match.
