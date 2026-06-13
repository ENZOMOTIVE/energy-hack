# Gauntlet backlog

Done so far: full gym (SPEC.md + DEVPLAN.md, M1-M8), arena mode with chaos
injection and judge-plays-it, real-data layer (Open-Meteo + SMARD) behind the
SYNTHETIC/REAL toggle, DeepSeek as a real leaderboard contestant, and the
intelligent test-case generator (genome + fitness + evolutionary search +
diversity selection + battery report; discrimination and adversarial modes;
opt-in LLM red-team author). Backend done and gated; UI tab is the open piece.

## Multi-worker + reports: remaining (deferred from the personas pass)

- Real-data leaderboard persona rows (today the personas are synthetic-only; the
  real board still shows the generic `deepseek` row).
- A 4th `ds-cost-focused` persona (prioritise avoiding crew fees and imbalance
  over coverage).
- Per-persona Monte-Carlo above 1 (today personas are a single run per case,
  labelled as such; bumping to 3 tightens the bands at 3x the API cost).
- Open a generated battery case in the replay view (shared with the item below).

## Generator: remaining

- UI: a GENERATOR/BATTERY tab. Show the curated battery (cards by failure-mode
  label + stake), the per-agent certification report (pass-rate bar + worst-case
  P10), the 'hardest day that breaks each agent' callout, and a discrimination
  vs adversarial toggle. A 'regenerate' button can hit a backend generate
  endpoint (deterministic, fast) or just switch among precomputed batteries.
- Optional: let a generated battery case open in the existing replay view
  (compile genome -> scenario -> trace on demand).
- Optional: richer genome (multi-fault days, partial-string faults, ramp events)
  so the evolutionary search has more room to beat random than in today's
  compact space.

## Priority 2: real LLMs

DONE: provider abstraction (`GAUNTLET_PROVIDER=anthropic|deepseek`), DeepSeek
JSON mode at temperature 0 with 429 retry, `.env` / `.env.example`, `deepseek`
as a leaderboard row on both boards (`make traces-deepseek`, results.json
merge-aware), live /simulate still mock-only, tests still mock-only.
Lessons already wired in: tranche-based eclipse payload, re-arm fault trigger
when the model declines, recent_weather_gap series for whipsaw days.

Still open:
1. `claude` row: plumbing exists (`--agents claude`), needs ANTHROPIC_API_KEY
   in .env, then add to traces-deepseek target (rename traces-llms).
2. One deepseek-reasoner run for a "watch it think" moment in the pitch.
3. Real-model rows as non-selectable arena fighters (today: leaderboard only;
   arena fighters stay mock for instant re-simulation).

## Demo readiness

6. Pitch deck + two rehearsals (eclipse facts: SPEC Appendix A; 3-min arc:
   DEVPLAN section 8; real-day facts: data/real/meta.json).
7. Projector check: fonts, dark theme, playback speed (200 ms/step arena,
   250 ms replay).

## Stretch ladder

8. MCTrader 4th contestant: samples production futures, no crew concept;
   should beat rules on trading and fail S2.
9. S3 fan chart from existing MC samples (P10/P90 band).
10. Negative-price handling done properly: today settlement floors real prices
    at 1 EUR/MWh to keep the oracle/floor bracket sound. The real feature is
    curtailment: at negative prices the right move is to NOT produce. New
    action + economics + a "negative price day" scenario. Strong Germany-2026
    story.
11. MC on real data: needs a multi-day real dataset (fetch a month, treat days
    as samples) instead of seeded variations. Note shown nowhere yet.
12. Deep Agents (LangChain) contestant as a framework-agnosticism flex, behind
    the same agent contract.

## Known modeling assumptions (state honestly if asked)

- Imbalance price = 2x DA proxy; intraday spread = +/-10% of DA.
- Single DE-LU price zone for Spanish parks.
- Eclipse obscuration as gaussian between published contact times.
- S3 evening price spike (1.5x, min 150) is our scenario assumption on top of
  real prices.
- Real-data mode: settlement floored at 1 EUR/MWh on negative-price hours.
