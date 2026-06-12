# Gauntlet: a stress-test gym for solar asset-management agents

Working name. Invertix Open Track (#1.2). Two builders, ~10 hours.

## One-liner

Invertix sells AI workers for solar parks. Gauntlet is the proving ground where those workers earn their license: a simulator that throws the worst days in energy at any agent and scores, in euros, what its reactions cost you.

## Why this wins the open track

- It is not a clone of the sponsor's product. It is the evals infrastructure an agent company needs internally and commercially but cannot justify building as a product.
- Trust is the adoption blocker for autonomous agents in energy. "Nobody should deploy an unmeasured agent on a real asset" is the thesis, demonstrated live.
- The gym wins even when our own agent loses. A mediocre LLM score is not a failed demo; it is the product argument.
- Hero scenario: the August 12, 2026 eclipse, the only pre-scheduled continent-scale stress test on the calendar, 8 weeks after the hackathon. See Appendix A.

## The 3-minute demo arc

1. Cold open with the eclipse fact: 2015, 90 GW installed, ENTSO-E called it a first-of-its-kind stress test. Today: 406 GW. Next test: August 12, 20:26 CEST.
2. Show the leaderboard: three agents (do-nothing, rule-based, LLM worker) ran the same three bad days. Scores are "% of recoverable losses recovered."
3. Replay the eclipse episode: three-curve chart, the shadow eats production, the LLM worker's action cards appear with reasoning, a running euro counter diverges from the do-nothing ghost line.
4. Replay the moment the rule-based agent fails (dispatches a repair crew at a weather bust, paying for a truck roll that fixes nothing) while the LLM correctly re-trades instead.
5. Close: "Before August 12, run your worker through ours."

## System overview

```
data/ (pre-downloaded)        backend/ (Python)                  frontend/ (React)
  weather JSON (Open-Meteo)     sim core (pvlib parks)             leaderboard view
  prices CSV (SMARD)            scenario engine                    episode replay view
  eclipse curves CSV            economics + scoring
                                agents (noop / rules / LLM)
                                FastAPI (serves traces + results)
```

Agents are Python classes inside the backend (no MCP, no agent-facing REST). FastAPI exists only to serve the React UI. Episodes run offline via a runner script; the UI replays stored JSON traces. Nothing live has to work during the pitch.

## Simulation core

- Portfolio: 3 parks. Zaragoza ES 50 MW (in eclipse totality), Valencia ES 40 MW (totality), Munich DE 30 MW (~88% obscuration).
- Timestep: 15 minutes. Episode: one day, 96 steps.
- Plant model: pvlib PVWatts-style (irradiance + temperature to AC power) per park. Real physics is the realism defense.
- Weather: real historical days from Open-Meteo archive API, pre-downloaded to `data/`. Forecast weather = a perturbed copy (time-shifted or smoothed), which gives us controlled forecast error.
- Eclipse: per-park obscuration curves precomputed to CSV from published local circumstances (Galicia contact 20:26 CEST, Munich max 88.8% at 20:16). Bell-curve interpolation between contact times, multiplied onto irradiance. Documented approximation, exactly right where it matters.

## Economics (simple, defensible, every number on screen traces to this)

- Day-ahead position: locked at episode start from the forecast curve, at real SMARD day-ahead prices for that day.
- Imbalance: each step, gap = scheduled minus actual; cost = gap x imbalance price (imbalance price = 2x day-ahead, punitive, stated as an assumption).
- Intraday re-trade: closing a predicted shortfall costs day-ahead x 1.10 (buying back), selling surplus earns day-ahead x 0.90. Crude but directionally honest spread.
- Crew dispatch: flat 500 EUR, repair completes 8 steps (2 h) after dispatch. Dispatching when nothing is broken burns the fee and flags a safety violation.
- Eclipse day: real price profile for the base day plus a stated spike multiplier 19:30-21:00 to reflect the evening ramp.

## Scenario definitions (seeded, replayable, identical for every agent)

| ID | Name | What happens | Correct response |
|----|------|--------------|------------------|
| S1 | cloudfront_bust | Forecast says sunny; front arrives 3 h early over DE | Re-trade the shortfall. Do NOT dispatch crew |
| S2 | silent_fault | Clear day; inverter failure at 11:00 kills 25% of Zaragoza | Dispatch crew fast, re-trade the residual gap |
| S3 | eclipse_day | Aug 12 2026 evening: deterministic obscuration on all three parks, plus an uncertain cloud layer over Valencia, plus price spike | Pre-trade the published curve early, react intraday to the cloud residual only, no crew |

S3 is the finale and the pitch centerpiece: it mixes a perfectly forecastable component with an unforecastable one, which is exactly what discriminates good agents from lucky ones.

Stretch scenario (build only if ahead of schedule): soiling_creep, a slow multi-day output decline, tests patience vs overreaction.

Implementation directive: write scenario parameters (front arrival time, fault onset and magnitude, cloud field) as seeded random draws from the start, even though core episodes run a single fixed seed. The Monte Carlo layer below reuses that machinery for free.

## Agent contract

```python
class Agent:
    def act(self, obs: Obs) -> Action: ...

# Obs: timestamp, DA forecast curve (locked), actuals so far (per park),
#      weather actuals so far + next-3h weather forecast, prices,
#      twin_expected: physics-expected output given ACTUAL weather (the gym
#      provides the twin so the contest is about reaction quality, not modeling)
# Action: one of
#   noop()
#   trade(park_id, delta_mw, remaining_hours)   # adjust scheduled position
#   dispatch_crew(park_id)
```

Three contestants ship at demo time:

1. `DoNothingAgent`: the floor.
2. `RuleAgent`: threshold logic (if actual < 0.8 x twin_expected for 2 steps, dispatch crew; if actual < 0.8 x DA forecast, re-trade). Deliberately naive: it cannot tell weather busts from faults, which produces the demo's failure moment in S1.
3. `LLMWorker`: Claude API. Prompt receives the obs summary including the gap decomposition (forecast-vs-weather gap = weather bust component, weather-vs-actual gap = plant component) and must return one action as JSON plus a one-sentence reason. The reason strings become the action cards in the replay UI. Numbers in cards come from the sim, never from the LLM.

## Scoring

For each (scenario, agent): run the episode, total all costs.

- `oracle`: scripted best response per scenario (knows the script: trades at first divergence with perfect foresight, dispatches crew at fault onset). Upper bound.
- `floor`: DoNothingAgent cost.
- Score = (floor_cost - agent_cost) / (floor_cost - oracle_cost), reported as "% of recoverable losses recovered," clamped to [0, 1].
- Safety metrics (shown as flags, not folded into score): false crew dispatches, trades against the gap direction, steps from event onset to first correct action.

The oracle/floor bracket makes scores immune to "the scenario was just hard" objections and gives the leaderboard a single honest currency. With the Monte Carlo layer enabled, that currency becomes a distribution instead of a point.

## Monte Carlo layer (stretch: build only when DoD items 1-4 are green)

Purpose: answer the judge question "isn't this leaderboard three hand-picked anecdotes?" by scoring agents across the space of bad days, not one realization of each.

- **Robustness scoring**: run N=500 seeded variations per scenario (S1: front arrival jittered 1-5 h early, thickness varied; S2: fault onset 09:00-15:00, magnitude 10-40%; S3: cloud field over Valencia randomized) for the cheap agents: DoNothing, RuleAgent, oracle. Report mean recovery % and worst-decile (P10) per cell. Episodes are pvlib arithmetic, so 500 runs cost seconds.
- **LLM sampling honesty**: the LLM worker gets 10-20 sampled episodes (API cost bound), reported as mean with a confidence interval. State this openly in the pitch; error bars are an evals company doing its job.
- **MCTrader, a fourth contestant (further stretch)**: no LLM. At each step it samples 500 production futures from forecast uncertainty and picks the trade minimizing expected cost. It has no concept of a repair crew, so it should beat the rules on S1/S3 trading and fail S2 outright. That contrast (rules vs stochastic optimizer vs LLM) makes the gym's discriminating power the story.
- **Fan chart (further stretch)**: the same samples give a P10/P50/P90 production band on the S3 replay screen. Fan charts are the native idiom of energy forecasting; domain judges read them as fluency.
- **What stays deterministic**: the rehearsed demo replay remains a single fixed-seed episode, and prices stay real SMARD data (no synthetic price process to defend).
- **Verifiable check**: `python -m backend.run --scenario S1 --agent rules --mc 500` writes a distribution JSON with 500 scores plus summary stats in under a minute, and `GET /results` carries mean/P10 fields when present.

Demo line this buys: "Our scores are distributions, not anecdotes. We ran every agent through 500 versions of each bad day."

## API (FastAPI, serves UI only)

- `GET /results` leaderboard JSON: scenarios x agents, scores, costs, safety flags
- `GET /episodes/{scenario}/{agent}` full replay trace: per-step curves, prices, actions, reasons, cumulative cost vs floor
- (stretch) `POST /run/{scenario}/{agent}` live re-run with SSE streaming of LLM reasoning

## UI (React via Vite, talks to FastAPI)

1. **Leaderboard**: grid of scenarios x agents, recovery %, EUR lost, safety flags. The reveal screen. Cells switch to mean + P10 (and a CI badge for the LLM) once Monte Carlo results exist.
2. **Episode replay**: time scrubber with play button; three-curve chart (expected-from-forecast, expected-from-actual-weather, actual); price strip; action cards appearing at their timestep with the agent's reason; running euro counter with the do-nothing ghost line.
3. (stretch, cut first) **Judge-plays-it**: same replay screen with the three action buttons enabled, judge's score lands on the leaderboard.

## The radar hedge

Decision point at hour 7, informed by Invertix mentor reaction in hour 1. If the gym framing is not landing, the same artifacts re-cut as "portfolio event radar" (product framing): same traces, same replay screen, pitch reframed around the LLMWorker as the product and the gym as our internal eval. Optional map view (parks as dots, shadow sweep on S3) is a ~2 h add behind this decision; do not build it before hour 7.

## Build plan: 2 builders, 10 hours

Hour 0.0-0.5, together: lock the trace JSON schema and Obs/Action types (this document's contract section is the draft), scaffold repo, talk to an Invertix mentor about the concept.

**Builder A (Python)**
- 0.5-3.0: sim core: park models, weather loaders, economics
- 3.0-4.5: scenario engine: S1, S2, S3 incl. eclipse curve CSVs
- 4.5-5.5: scoring: oracle scripts, floor, recovery %
- 5.5-7.0: RuleAgent + LLMWorker, run all 9 episodes, write traces
- 7.0-8.5: FastAPI endpoints, integration, tune S1/S2 thresholds until the demo story reproduces deterministically
- 8.5-10: if DoD 1-4 are green, climb the stretch ladder (Monte Carlo robustness scoring first, then MCTrader); otherwise pitch support, numbers for slides, dry runs

**Builder B (React + pitch)**
- 0.5-2.0: Vite scaffold, mock trace data from the agreed schema
- 2.0-5.0: episode replay screen (chart, scrubber, action cards, euro counter)
- 5.0-6.5: leaderboard screen
- 6.5-8.0: real data integration + polish (or map view if hour-7 decision says radar)
- 8.0-10: pitch deck + two full rehearsals

**Cut lines, in order**: judge-plays-it; live SSE run; map view; S1 (keep S2 + S3 if a scenario must go); safety flags in UI (keep in pitch verbally).

**Stretch ladder, in order (build only if ahead, never blocks DoD)**: Monte Carlo robustness scoring; MCTrader agent; S3 fan chart; soiling_creep scenario.

## Definition of done (verifiable, per check)

1. `python -m backend.run --scenario S3 --agent llm` writes `traces/S3_llm.json` containing 96 steps, at least 2 actions with reasons, and a score in [0, 1].
2. `GET /results` returns 9 entries (3 scenarios x 3 agents) with floor < oracle costs ordering correct for every scenario.
3. The replay UI at localhost:5173 plays S3 end-to-end: curves animate, at least 3 action cards appear, euro counter diverges from the ghost line.
4. RuleAgent provably fails S1 (false crew dispatch flag set) and LLMWorker does not. This is the demo's drama beat; it must be reproducible, not hoped for.
5. Full pitch run-through under 3 minutes using only stored traces, network cable unplugged.

## Pre-download checklist (do before leaving home wifi)

- [ ] Open-Meteo archive JSON for the 3 park locations, chosen base days
- [ ] SMARD day-ahead price CSVs for the same days
- [ ] Eclipse local-circumstance numbers (already in Appendix A) turned into `data/eclipse_curves.csv`
- [ ] pip/npm dependency caches warm (`pvlib`, `fastapi`, `uvicorn`, `anthropic`; `vite`, `react`, charting lib)
- [ ] Claude API key tested

## Out of scope (say no fast)

Real plant data, MCP interface, RL training, multi-day episodes, auth, cloud deployment (runs on a laptop), battery/storage modeling, more than 3 parks.

## Appendix A: eclipse facts for the pitch (verified 2026-06-12)

- Total solar eclipse Tuesday, August 12, 2026, early evening. Totality crosses Iceland and a 290 km band of northern Spain: Bilbao, Santander, Valladolid, Burgos, Zaragoza, Valencia. Madrid and Barcelona at 99.9%.
- Shadow reaches Galicia 20:26 CEST, exits the mainland ~20:31. Sun ~11 degrees high. Totality under 2 minutes.
- Munich: partial ~86-89%, 19:23 to 21:07 CEST, max 20:16, sun sets before eclipse ends.
- 2015 precedent: at ~90 GW EU solar, the March 2015 eclipse removed ~17 GW and reintegrated ~25 GW at 3x normal ramp rates; ENTSO-E ran months of preparation and called it a first-of-its-kind stress test. EU solar is now ~406 GW (4.5x), heading for ~671 GW by 2028.
- Judge rebuttals: (1) evening timing means below-peak output, but the eclipse steepens the dive into the evening demand ramp when intraday prices are spikiest, and 4.5x capacity makes evening fractions GW-scale; (2) "eclipses are rare": Iberia gets three in three years (total 2026, total mid-morning 2027 over southern Spain, the real monster; annular 2028). 2026 is the dress rehearsal.

Sources: Wikipedia (Solar eclipse of August 12, 2026), BBC Sky at Night, TheSkyLive (Munich circumstances), CleanTechnica + ENTSO-E (2015 numbers), SolarPower Europe (capacity data).
