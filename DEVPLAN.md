# Gauntlet Dev Plan (one-shot build instructions)

Companion to SPEC.md. SPEC.md is the "what and why"; this file is the "exactly how."
Every design decision is already made here. If this file and your judgment disagree,
follow this file. If this file is genuinely ambiguous, pick the simplest option that
keeps the verification gates green and note the choice in a code comment.

## 0. Instructions to the build agent

1. Read SPEC.md first, then this file fully, before writing code.
2. Build milestones M1 to M7 strictly in order. Each milestone ends with a
   verification gate (a command and its expected result). Run the gate, fix until
   green, then move on. Do not start milestone N+1 with a red gate at N.
3. M8 (Monte Carlo) is optional: build it only if M1-M7 are all green.
4. Do not gold-plate: no auth, no docker, no CI, no logging frameworks, no abstract
   base classes beyond what is specified, no extra agents, no extra endpoints.
5. The whole system must work offline with no API keys. The Anthropic call path is
   behind a flag (section 4.6). All weather and price data is generated
   deterministically by committed code; nothing fetches the network at runtime.
6. Times: everything runs in fixed UTC+2 (CEST). Use naive datetimes plus a constant
   offset or pandas with tz="Etc/GMT-2". Do not mix timezones. The simulated day for
   all scenarios is 2026-08-12, 00:00 to 23:45, 96 steps of 15 minutes.
   Step index k covers [k*15min, (k+1)*15min). step_hours = 0.25.


## 1. Repository layout (exact)

```
backend/
  requirements.txt
  gauntlet/
    __init__.py
    config.py        # constants: parks, prices, seeds, economics params
    weather.py       # clear-sky + cloud factors per scenario
    eclipse.py       # obscuration curves
    parks.py         # power model
    scenarios.py     # S1, S2, S3 definitions + seeded parameter draws
    sim.py           # episode engine + economics + trace building
    oracle.py        # per-scenario perfect-response cost
    agents/
      __init__.py
      base.py        # Agent protocol, Obs/Action types
      noop.py        # DoNothingAgent
      rules.py       # RuleAgent (deliberately naive)
      llm.py         # LLMWorker + deterministic MockLLM fallback
      mc_trader.py   # M8 only
    scoring.py       # recovery %, safety flags
    run.py           # CLI: python -m gauntlet.run --scenario S1 --agent rules
    api.py           # FastAPI app
  tests/
    test_sim.py
    test_scenarios.py
    test_drama.py
frontend/
  (Vite + React + TypeScript app, section 7)
traces/              # runner output, JSON per (scenario, agent). Committed.
Makefile
SPEC.md
DEVPLAN.md
README.md
```

## 2. Dependencies

backend/requirements.txt:
```
pvlib>=0.11
numpy
pandas
fastapi
uvicorn
anthropic
pytest
httpx        # for FastAPI test client
```
Python 3.11+. Frontend: Node 20+, Vite, React 18+, TypeScript, recharts.
No other runtime dependencies.

Makefile targets:
```
make traces   # run all (scenario, agent) pairs -> traces/*.json
make test     # pytest backend/tests
make api      # uvicorn gauntlet.api:app --port 8000
make ui       # cd frontend && npm run dev
make demo     # make traces, build frontend, serve everything at :8000
```

## 3. Shared constants (config.py)

```python
PARKS = {
  "zaragoza": {"name": "Zaragoza ES", "p_mw": 50.0, "lat": 41.65, "lon": -0.88},
  "valencia": {"name": "Valencia ES", "p_mw": 40.0, "lat": 39.47, "lon": -0.38},
  "munich":   {"name": "Munich DE",   "p_mw": 30.0, "lat": 48.14, "lon": 11.58},
}
PERF_RATIO = 0.90          # flat performance ratio, no temperature model
IMBALANCE_MULT = 2.0       # shortfall pays 2x DA per MWh
BUYBACK_MULT = 1.10        # reducing schedule buys back at 1.1x DA
SELLMORE_MULT = 0.90       # increasing schedule sells at 0.9x DA
CREW_FEE_EUR = 500.0
REPAIR_STEPS = 8           # crew fixes fault 8 steps (2h) after dispatch
DEFAULT_SEED = 42
SIM_DATE = "2026-08-12"
N_STEPS = 96
```

Day-ahead price curve (EUR/MWh), same for all scenarios, by hour h:
```
h in [0,6): 55   [6,9): 85   [9,16): 45   [16,19): 95   [19,22): 130   [22,24): 75
S3 only: hours [19.5, 21.0) override to 180  (stated assumption: eclipse evening spike)
```
Expand to 96 values (each hour value repeated 4x; the 19.5 boundary lands on a step).

## 4. Backend behavior, module by module

### 4.1 weather.py

- `clearsky_ghi(park) -> np.array[96]`: pvlib `Location(lat, lon, tz="Etc/GMT-2").get_clearsky(times, model="ineichen")["ghi"]`
  for the 96 timestamps of SIM_DATE. This is the only pvlib usage.
- `cloud_factor(scenario, park, kind, rng) -> np.array[96]` where kind is
  "forecast" or "actual". Values in [0,1], default all 1.0. Scenario specifics in 4.4.

### 4.2 eclipse.py

Obscuration curve per park: gaussian bell
`obs(t) = max_obs * exp(-((t - t_max)/sigma)**2)`, zero outside 19:20-21:10 CEST.

| park | t_max (CEST) | max_obs | sigma (min) |
|------|--------------|---------|-------------|
| zaragoza | 20:29 | 1.00 | 25 |
| valencia | 20:30 | 1.00 | 25 |
| munich   | 20:16 | 0.888 | 30 |

`obscuration(park) -> np.array[96]` (evaluate at step midpoints). These numbers come
from published local circumstances (SPEC Appendix A); the gaussian shape is a
documented approximation.

### 4.3 parks.py

```
power_mw(park, ghi_eff) = clip(park.p_mw * (ghi_eff / 1000.0) * PERF_RATIO, 0, park.p_mw)
ghi_eff = clearsky_ghi * cloud_factor * (1 - obscuration_if_S3)
fault: while active, park output *= (1 - fault_magnitude)
```
No temperature model, no inverter model. Keep it to these lines.

### 4.4 scenarios.py

Each scenario produces, per park: `forecast_power[96]`, `actual_power[96]`,
`twin_power[96]`, plus `known_events` (list of dicts) and fault metadata.

Definitions (all draws use `rng = np.random.default_rng(seed)`; default seed 42
gives the canonical demo episode):

**S1 cloudfront_bust** (Munich only; Spanish parks clear all day)
- Forecast weather: front over Munich 17:00-19:00, cloud_factor 0.40 during it,
  linear 30 min ramps on both edges.
- Actual weather: front arrives early: start = 14:00 + U(-60, +60) min (seed 42
  draw), cloud_factor 0.35, ends 18:30, same ramps.
- No fault. known_events = [].

**S2 silent_fault** (clear day everywhere, forecast == actual weather)
- Fault on zaragoza: onset 11:00 + U(-120, +240) min, magnitude U(0.15, 0.40)
  (canonical seed gives roughly 11:00 / 0.25). Active until repaired or end of day.
- Fault affects `actual_power` only, never `twin_power`. known_events = [].

**S3 eclipse_day**
- Obscuration applied to actual and twin for all three parks.
- Forecast EXCLUDES the obscuration and the clouds (story: the naive forecast
  pipeline missed the eclipse; the agent that reads the calendar wins).
- Valencia cloud field, actual only: 18:00-21:00, cloud_factor = seeded random walk
  clipped to [0.55, 1.0] (step: +N(0, 0.06) per 15 min, start 0.9).
- No fault.
- known_events = one entry per park:
  `{"type": "solar_eclipse", "park": ..., "window": "19:20-21:10",
    "max_obscuration": ..., "t_max": ...}`

twin_power = power from ACTUAL weather (including obscuration and clouds), no fault.
So: plant_gap = twin - actual (nonzero only for faults),
weather_gap = forecast - twin (weather bust + eclipse).

### 4.5 sim.py: episode engine and economics

State per episode: `schedule[96]` per park, initialized to `forecast_power`,
cumulative costs, safety counters, action log.

Step loop (k = 0..95): build Obs, call `agent.act(obs)`, apply action, then settle:

```
gap_mw = schedule[k] - actual[k]                  # per park, then summed effects
if gap_mw > 0:  cost += gap_mw * 0.25 * IMBALANCE_MULT * da_price[k]   # shortfall
if gap_mw < 0:  pass                              # surplus: given away, no revenue
```

Actions (at most one per step):
- `noop()`
- `trade(park_id, delta_mw, hours, start_step=None)`: applies to `hours` worth of
  steps beginning at `max(k+1, start_step)`; start_step defaults to "next step"
  and exists so known future events (the eclipse) can be pre-traded at step 0.
  `schedule[park][t] = clip(schedule + delta_mw, 0, p_mw)`.
  Settlement at execution time, per affected step, charged on the APPLIED
  (post-clip) delta, not the requested one:
  applied < 0 (buy back): `cost += |applied| * 0.25 * BUYBACK_MULT * da_price[t]`
  applied > 0 (sell more): `cost -= applied * 0.25 * SELLMORE_MULT * da_price[t]`
- `dispatch_crew(park_id)`: `cost += CREW_FEE_EUR`. If the park has an active
  fault, it clears at step k + REPAIR_STEPS. If not, `false_dispatch += 1` and
  nothing else happens. A second dispatch to the same park is a no-op plus fee.

Obs (a dataclass; also serialized into the LLM prompt):
```
step, time_iso, da_price[96],
per park: forecast[96], actual[0..k], twin[0..k], schedule[k..95],
known_events, crew_dispatched: dict[park, bool]
```

Trace JSON written per episode (this schema is the frontend contract, do not drift):
```json
{
  "scenario": "S3", "agent": "llm", "seed": 42,
  "parks": ["zaragoza", "valencia", "munich"],
  "steps": [
    {"k": 0, "time": "2026-08-12T00:00+02:00",
     "forecast_mw": {"zaragoza": 0.0, ...},
     "twin_mw": {...}, "actual_mw": {...}, "schedule_mw": {...},
     "da_price": 55.0, "cum_cost_eur": 0.0, "cum_cost_floor_eur": 0.0,
     "action": null}
  ],
  "actions": [
    {"k": 31, "type": "trade", "park": "munich", "delta_mw": -8.0, "hours": 4,
     "start_step": 32, "false_dispatch": false,
     "reason": "Actual is tracking weather-expected; this is a forecast bust, ..."}
  ],
  "totals": {"cost_eur": ..., "floor_eur": ..., "oracle_eur": ..., "score": ...,
             "false_dispatches": 0, "steps_to_first_action": 31}
}
```
`cum_cost_floor_eur` is the do-nothing cost replayed alongside (the ghost line).

### 4.6 agents/

`base.py`: `Obs`, `Action` dataclasses and `class Agent: def act(self, obs) -> Action`.

`noop.py`: always noop.

`rules.py` RuleAgent, DELIBERATELY NAIVE. It never reads `twin` or `known_events`:
- If `actual < 0.8 * forecast` for 2 consecutive steps at a park and no crew sent
  yet: `dispatch_crew(park)` (this is the engineered failure: it fires on S1's
  cloud front and on S3's eclipse).
- One step after dispatching for a park: `trade(park, -(forecast[k]-actual[k]), 4)`.
- One action per step, crew checks take priority over trades.

`llm.py` two classes behind one factory `make_llm_agent()`:
- `MockLLM` (default, used when env `GAUNTLET_USE_ANTHROPIC` is unset or no
  `ANTHROPIC_API_KEY`): deterministic policy that uses the decomposition correctly:
  - step 0: if known_events, for each affected park pre-trade the eclipse energy:
    `trade(park, -mean_obscured_mw_over_window, 2)` where the mean comes from the
    event's max_obscuration applied to the forecast in the window.
  - On trigger steps: if `plant_gap > 0.10 * p_mw` for 2 consecutive steps and no
    crew sent: dispatch_crew, next step trade the residual.
    Elif `weather_gap > 0.10 * p_mw` for 2 consecutive steps: trade(-weather_gap, 3).
  - Reasons are template strings stating the decomposition numbers.
- `LLMWorker` (env flag on): same trigger policy for WHEN to call, but the action
  comes from the Anthropic API. Model: env `GAUNTLET_MODEL`, default
  `claude-sonnet-4-6`. Call budget: step 0 plus trigger steps, minimum 4 steps
  between calls, hard cap 12 calls/episode; outside calls, noop.
  Prompt: system = 6 lines explaining the role, the action JSON schema, and that
  numbers must come from the obs; user = compact JSON with current step,
  decomposition per park (plant_gap, weather_gap, last 8 steps), prices now and
  next 3 h, known_events, crew state. Force JSON output:
  `{"action": "trade|dispatch_crew|noop", "park": ..., "delta_mw": ...,
    "hours": ..., "reason": "one sentence"}`. On any parse failure: retry once,
  then noop. Clamp delta_mw to [-p_mw, p_mw].
  Traces must record which brain ran: `"agent": "llm"` plus `"brain": "mock"|"anthropic"`.

### 4.7 oracle.py

Computable analytically, no search:
- Schedule matched to true actuals from step 0: oracle cost =
  `sum over shortfall steps of true_gap * 0.25 * BUYBACK_MULT * da_price` where
  true_gap = forecast - actual when positive (it buys back exactly what it will
  miss, paying 1.1x instead of the 2.0x penalty).
- S2 additionally: dispatch at fault onset (fee + the residual gap during the
  8 repair steps, bought back at 1.1x). Oracle never false-dispatches.

### 4.8 scoring.py and run.py

`score = clip((floor - agent_cost) / (floor - oracle), 0, 1)`.
Safety flags: `false_dispatches`, `steps_to_first_action` (first non-noop after the
scenario's event onset step, defined per scenario in scenarios.py).

run.py CLI:
```
python -m gauntlet.run --scenario S1 --agent rules [--seed 42] [--out traces/]
python -m gauntlet.run --all          # 3 scenarios x {noop, rules, llm}
```
`--all` writes 9 trace files plus `traces/results.json` (the leaderboard payload).

### 4.9 api.py

FastAPI, CORS allow `http://localhost:5173`.
- `GET /results` -> contents of traces/results.json
- `GET /episodes/{scenario}/{agent}` -> the trace JSON
- Serve `frontend/dist` as static files at `/` when the directory exists.
No other endpoints. Reads from disk on each request; no caching, no state.

## 5. Milestones and verification gates

**M1 sim core**: config, weather (clear-sky only), parks, sim engine with noop agent,
economics on a hand-made toy scenario inside the test.
GATE: `pytest backend/tests/test_sim.py` green. Test must include a hand-computed
case: 4 steps, flat price 100, schedule 10 MW, actual 8 MW
=> imbalance = 2 MW * 0.25 h * 2.0 * 100 = 100 EUR per step.

**M2 scenarios**: scenarios.py, eclipse.py, cloud factors, twin computation.
GATE: `pytest backend/tests/test_scenarios.py` green, asserting with seed 42:
S1 Munich actual dips below 0.5x forecast somewhere in 14:00-18:00 while
zaragoza forecast == actual everywhere; S2 plant_gap > 0 only on zaragoza after
onset and twin == forecast all day; S3 weather_gap on all parks within
19:20-21:10 with peak at the park's t_max +/- 2 steps, and forecast has no dip.

**M3 floor, oracle, scoring**: noop runs, oracle.py, scoring.py, run.py single mode.
GATE: `python -m gauntlet.run --scenario S2 --agent noop` writes a trace;
pytest asserts for all 3 scenarios: `oracle < floor` strictly, and noop score == 0.

**M4 rules + mock LLM + the drama beat**: rules.py, llm.py (mock path), `--all`.
GATE: `pytest backend/tests/test_drama.py` green:
- S1: rules trace has false_dispatches >= 1; llm(mock) has 0.
- S3: rules false_dispatches >= 1; llm(mock) has 0 and its first action is at step 0.
- For every scenario: 0 <= score(rules) and score(llm) <= 1, and
  score(llm) > score(rules) on S1 and S3.
- S2: both dispatch crew; llm steps_to_first_action <= rules'.
If a drama assertion fails, tune RuleAgent thresholds or scenario magnitudes
(front depth, fault size) until it passes deterministically. These assertions ARE
the demo; they are the most important gate in this plan.

**M5 API**: api.py.
GATE: with traces generated, `httpx` test client gets 200 + valid JSON from
`/results` and `/episodes/S3/llm`; `/results` has exactly 9 entries.

**M6 frontend**: section 7.
GATE: `npm run build` succeeds; manual check in the plan's section 8 script.

**M7 demo assembly**: Makefile, README (how to run, 10 lines), `make demo` serves
the built UI + API on :8000.
GATE: `make demo` from a clean checkout (fresh venv + npm install) reaches a
browsable leaderboard at http://localhost:8000 using only committed code. Replay
of S3/llm plays end to end.

**M8 (OPTIONAL) Monte Carlo layer**: only if M1-M7 green. `--mc N` on run.py:
N seeded variations (seeds = range(1000, 1000+N)) for noop, rules, oracle
(and mock llm capped at N=20). Writes `traces/mc_{scenario}.json` with per-agent
score arrays + mean + p10. `/results` includes `mc: {mean, p10, n}` when present.
Leaderboard cells show "mean (P10)" when mc exists.
GATE: `python -m gauntlet.run --scenario S1 --agent rules --mc 200` finishes
< 60 s and mean/p10 are within [0, 1]; ordering oracle-mean=1.0 > llm-mean >
noop-mean=0.0 holds on S1.

## 6. Expected qualitative outcomes (use as your mental test table)

| | noop | rules | llm (mock) |
|---|---|---|---|
| S1 | score 0 | false crew dispatch at the front, late trade, low score | no dispatch, trades the bust, high score |
| S2 | score 0 | dispatches (correctly), decent score | dispatches faster + trades residual, best score |
| S3 | score 0 | false dispatch at eclipse, panic trades late | pre-trades at step 0 from known_events, reacts to Valencia clouds only, best score |

## 7. Frontend spec (Vite + React + TS + recharts)

Single-page app, no router: a tab state `"leaderboard" | "replay"`.
`VITE_API_URL` env, default `http://localhost:8000`.

**Leaderboard view**: fetch `/results`. Table: rows = agents, columns = scenarios,
cell = score as "% recovered" + EUR lost underneath + red flag icon when
false_dispatches > 0. Click a cell -> replay view for that (scenario, agent).
If `mc` present, cell shows "mean% (P10%)".

**Replay view**: fetch `/episodes/{scenario}/{agent}`. Layout top to bottom:
1. Header: scenario + agent + final score.
2. ThreeCurveChart (recharts LineChart, x = the 96 steps): portfolio-summed
   forecast_mw (dashed), twin_mw (thin), actual_mw (bold). Only data up to the
   current playhead is rendered. A thin secondary area strip for da_price.
3. Transport: play/pause button + range slider (0..95). Play advances 4 steps/sec.
4. EuroCounter: `cum_cost_eur` at playhead vs `cum_cost_floor_eur` ghost value,
   big numbers, the difference in green.
5. ActionCardList: cards from `actions` with k <= playhead, newest on top:
   "[20:15] TRADE munich -8 MW for 4 h" + the reason sentence. Crew dispatch cards
   get a truck icon; on a step where the trace marks false_dispatch, style the
   card red with the label "wasted truck roll".

Keep components in `src/components/`: `Leaderboard.tsx`, `Replay.tsx`,
`ThreeCurveChart.tsx`, `EuroCounter.tsx`, `ActionCards.tsx`, `api.ts`, `types.ts`
(mirror the trace schema exactly). No state libraries; useState + props.

## 8. Demo run script (what a human does after `make demo`)

1. Open http://localhost:8000 -> leaderboard with 9 cells, llm row leading.
2. Click S1/rules -> replay shows the red "wasted truck roll" card at the front.
3. Click S3/llm -> press play: eclipse eats the curves, step-0 pre-trade card,
   euro counter diverges from ghost.
This sequence is SPEC.md DoD item 5; it must work with the network unplugged.

## 9. Explicit non-goals for the one-shot

MCTrader agent, fan chart, judge-plays-it mode, SSE live runs, map view, real
Open-Meteo/SMARD loaders, soiling scenario, deployment. These are post-one-shot
refinements; stubs and TODOs for them are also unwanted.
