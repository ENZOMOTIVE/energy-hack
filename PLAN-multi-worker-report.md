# Plan: multiple LLM workers + downloadable test report

Approved feature plan. Adds several DeepSeek "personas" as competing LLM workers,
a downloadable PDF report and CSV of the generated test cases plus results, and
two comparison graphs. Hand this file to the implementer to kick off.

## Decisions (approved)

1. **Workers differ by prompt persona.** One model (DeepSeek), three doctrines in
   the system prompt. Triggers (WHEN to call) stay shared; only the action
   doctrine changes.
2. **Comparison + export live in the Test Lab AND the leaderboard.**
3. **Export is server-side.** Backend renders a typeset PDF and streams a CSV.
4. **Two comparison graphs:** grouped bars by failure mode, plus a risk-return
   scatter. Both on-screen (recharts) and embedded in the PDF (matplotlib).

## Worker roster

Defined once in `backend/gauntlet/agents/personas.py` and reused everywhere
(leaderboard rows, battery contestants, UI labels).

| id            | label      | doctrine paragraph appended to the base system prompt |
|---------------|------------|--------------------------------------------------------|
| `ds-cautious`   | Cautious   | act only on unambiguous signals; trade ~70% of the computed gap; short 1-2h horizons; dispatch a crew only on a large sustained fault; prefer under-hedging to overreacting. |
| `ds-balanced`   | Balanced   | today's worker: trade the full computed gap; moderate 2-3h horizons; dispatch crew on confirmed sustained faults. |
| `ds-aggressive` | Aggressive | act on the first clear signal; trade the full gap; long 3-4h lock-in horizons; dispatch crews promptly on any sustained hardware gap. |

Count is tunable. A 4th `ds-cost-focused` (prioritize avoiding crew fees and
imbalance over full coverage) is an easy later add.

## Core constraint: real DeepSeek means frozen precompute

Real API calls are nondeterministic and too slow for per-page-load runs, so
persona results are a precomputed, committed artifact (same pattern as the
existing `deepseek` leaderboard row). The live demo stays fully offline; only a
one-time `make` step touches the API.

- Deterministic contestants (noop, rules, mock-llm) keep their 16-run
  Monte-Carlo per case.
- Personas run once per case (mc_n=1) to bound cost. Pass-rate and P10 for
  personas are computed over the 30 per-case scores and labelled single-run in
  the report, so the statistical basis is stated honestly. Tunable to mc_n=3 for
  tighter bands at 3x the cost.
- All persona calls run at temperature 0. Committed numbers are a frozen
  snapshot; `make battery-personas` refreshes them.
- Gating tests stay on the deterministic mock substrate (never the real API).

Rough precompute cost: battery is ~30 cases x 3 personas x up to 12 calls per
episode; leaderboard is 3 scenarios x 3 personas x up to 12. A few minutes and a
small spend, one time.

## Backend changes

- `agents/personas.py`: `PERSONAS` registry (id, label, doctrine). Helper to
  build a persona worker.
- `agents/llm.py`: `LLMWorker` gains a `persona` param that swaps in the doctrine
  paragraph after the base `SYSTEM_PROMPT`. No change to the trigger layer.
- `genome.py`: add `category()` returning `FAULT | WEATHER | ECLIPSE | COMBO`,
  derived from the genome (fault only, busts only, eclipse present, or a mix).
- `battery.py`: a persona pass that runs each persona once per case and merges
  per-case scores plus a summary block into the battery JSON. Per-case
  `category` recorded on each case for grouping.
- `run.py`: `--agents ds-cautious,ds-balanced,ds-aggressive` precomputes the
  three as leaderboard rows on S1/S2/S3 (synthetic). Retire the generic
  `deepseek` row in favor of `ds-balanced`. Fold into `make traces-deepseek`.
- `Makefile`: `battery-personas` target (needs `DEEPSEEK_API_KEY`); merges
  persona results into the committed battery JSON.
- New pip-only deps (no system libraries): `reportlab` (PDF document) and
  `matplotlib` (render the two charts to PNG for embedding). Add to
  `backend/requirements.txt`.

### Report endpoints (`api.py`)

- `GET /report/battery/{mode}.csv`
  One row per generated case. Columns: `case_name`, `failure_mode`, `label`,
  `stake_eur`, `floor_eur`, `oracle_eur`, `fitness`, then for each worker
  `<worker>_score` (mean) and `<worker>_pass` (0/1 at the TAU threshold).
  Pure Python `csv`, no deps.
- `GET /report/battery/{mode}.pdf`
  Typeset report via reportlab. Sections:
  1. Title, subtitle, meta line (mode, k cases, seed, report date stamped with
     `datetime.now()`).
  2. Methodology paragraph (what the battery is; fitness = recoverable money at
     stake times agent separation; Monte-Carlo; worst-case P10).
  3. Certification table: workers x {pass-rate, P10, mean, hardest day}, with the
     single-run note on persona rows.
  4. Comparison chart 1: grouped bars by failure mode (matplotlib PNG).
  5. Comparison chart 2: risk-return scatter (matplotlib PNG).
  6. Case appendix table: cases x stake x per-worker score.

## The two comparison graphs

On-screen with recharts; in the PDF with matplotlib (drawn separately from the
same numbers).

1. **Grouped bars by failure mode.** x = FAULT / WEATHER / ECLIPSE / COMBO; one
   bar per worker; y = mean recovered score. Shows who is strong where.
2. **Risk-return scatter.** Each worker is a point: x = pass-rate (reward),
   y = worst-case P10 (tail risk). Shows safe-but-mediocre versus
   bold-but-volatile.

## Frontend changes

API client (`api.ts`): types for the extended battery payload (per-worker
results, per-case category); helpers to hit the two report endpoints (trigger a
file download).

**Test Lab** (`components/Generator.tsx`), top to bottom:
1. mode toggle (discrimination / adversarial), as today.
2. two download buttons: "Download PDF report", "Download CSV".
3. certification report table, now all six workers as rows.
4. new "Worker Comparison" section: grouped bars and the scatter side by side.
5. case grid; cards get a compact six-worker score strip.

**Leaderboard** (`components/Leaderboard.tsx`): the three personas added as rows
under noop / rules / mock-llm, with a light "LLM workers" grouping so the
head-to-head reads cleanly. Synthetic mode.

Styles in `styles.css` for the comparison section, download buttons, and the
leaderboard worker grouping.

## Scope boundaries (not in this pass; add to TODO.md)

- Real-data persona rows on the leaderboard.
- The 4th cost-focused persona.
- Per-persona Monte-Carlo above 1.
- Opening a battery case in the replay view.

## Build order (each step a verifiable gate, each committed)

1. **Personas + `category()` + deterministic tests.** No API. Gate: tests green;
   the three persona prompts differ; `category()` classifies known genomes.
2. **Persona precompute** for battery and leaderboard; commit the frozen
   artifacts. Gate: battery JSON and results.json carry the three persona rows
   with sane scores; demo loads offline.
3. **CSV + PDF endpoints.** Gate: both files download, open cleanly, and contain
   the certification table, both charts, and the case rows with correct numbers.
4. **Test Lab UI + leaderboard rows.** Gate: build, serve, exercise over HTTP;
   the two charts render, the downloads work, the leaderboard shows the personas.

## Verification notes

- Browser click-through is the real UI check. This environment cannot drive a
  browser, so verify via type-check, production build, HTTP responses, and the
  served bundle; state that level honestly and leave the visual pass to Edwin.
- Keep all authorship clean (no AI attribution in commits, PRs, comments,
  files). Prose style rules apply to the report copy too (no em-dashes, etc.).
