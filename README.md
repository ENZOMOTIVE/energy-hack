# Gauntlet

The proving ground for solar asset-management agents. A deterministic simulator
throws bad days (cloud-front forecast busts, silent hardware faults, the
Aug 12 2026 eclipse) at any agent and scores, in euros, what its reactions cost.
See SPEC.md for the concept and DEVPLAN.md for the architecture.

## Run it

```
make setup    # venv + pip + npm install (once)
make test     # all gates: economics, scenarios, drama beats, API
make demo     # generate traces, build UI, serve everything at http://localhost:8000
```

Dev mode: `make api` (backend on :8000) plus `make ui` (Vite on :5173).

## Real data

The SYNTHETIC/REAL toggle in the UI switches between the deterministic synthetic
world and real days: Open-Meteo day-ahead forecasts vs archived actuals per park
plus SMARD DE-LU day-ahead prices (single-zone assumption). S1's weather bust is
a real forecast error that really happened. `data/real/` ships in the repo;
refresh or re-pick days with `make fetch-data` (network, once), then
`make traces-real`. Negative real prices are floored to 1 EUR/MWh in settlement
(displayed unfloored); see TODO.md.

## Real LLM brains

By default the LLM worker runs a deterministic mock (offline, reproducible).
Real models enter the leaderboard as extra contestants with precomputed traces;
the live arena stays mock-only so chaos injections re-simulate instantly.

Copy `.env.example` to `.env`, add keys, then `make traces-deepseek` adds a
`deepseek` row to both the synthetic and real boards (temperature 0,
`deepseek-chat`, JSON mode). `--agents claude` does the same via the Anthropic
API (default model claude-sonnet-4-6, override with `GAUNTLET_MODEL`).

`GAUNTLET_PROVIDER=anthropic|deepseek` instead swaps the brain inside the
default `llm` agent slot for `make traces` (legacy `GAUNTLET_USE_ANTHROPIC=1`
still works). Tests always run the mock.
