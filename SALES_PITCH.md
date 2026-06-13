# Gauntlet: The Sales Playbook

*Every feature we ship, translated into a reason the buyer signs.*

This is the field guide for selling Gauntlet. It walks each capability we built and answers the only question a buyer actually asks: **"what does this do for me?"** Use it to run a demo, write a proposal, or handle an objection.

---

## The 30-second pitch

Energy companies are deploying autonomous agents that move real money on real assets faster than they can prove those agents are safe. There is no standard, fast, neutral way to answer *"is this agent safe to let it act?"* That single question is the #1 blocker stalling paid pilots before they convert to production.

**Gauntlet is the proving ground.** We throw the worst days in energy at any agent (cloud-front forecast busts, silent hardware faults, the August 12 2026 eclipse) and score, in euros, exactly what its reactions cost. The buyer walks away with an independent certificate: *"this agent recovered X% of recoverable losses, against Y% for the baseline, across 500 versions of every bad day."*

We do not sell the agent. We sell the proof that the agent works.

---

## Why this lands: the buyer's problem, in their words

| Buyer | What keeps them up at night | What Gauntlet hands them |
|---|---|---|
| **Agent companies** (Invertix and peers) | "Our customers won't hand mission-critical autonomy to an agent they can't independently verify. Trust is killing our conversion rate." | A neutral certificate the sales team puts on the table. Turns "we think it's safe" into "here is the proof." |
| **Asset operators** (solar parks, funds) | "I'm about to let software trade and dispatch crews on my plant. How do I know it won't torch a contract on a bad day?" | A resilience score and a frame-by-frame replay of how the agent behaves under stress, before it touches the asset. |
| **Grid operators / regulators** | "How do I certify that autonomous agents on the grid keep it safe?" | An auditable, physics-based stress battery with every euro on screen traceable to a stated assumption. |

The common thread: **nobody should deploy an unmeasured agent on a real asset.** We make the measurement.

---

## The killer demo (run this, in this order)

The product sells itself in three minutes. Open the laptop, network cable unplugged, everything runs on stored traces.

1. **Cold open with the eclipse.** August 12 2026, early evening: a total solar eclipse crosses a 290 km band of northern Spain (Zaragoza, Valencia) and dims Munich ~88%. In 2015, at ~90 GW of EU solar, the eclipse pulled ~17 GW off the grid and ENTSO-E ran months of prep. EU solar is now ~406 GW, 4.5x larger. This is the only pre-scheduled, continent-scale stress test on the calendar, and it is 8 weeks out. *"Before August 12, run your worker through ours."*

2. **Show the leaderboard.** Three agents (do-nothing, rule-based, LLM worker) ran the same bad days. One honest currency on every cell: **% of recoverable losses recovered.** No vanity metric.

3. **Replay the eclipse episode.** The three-curve chart shows the shadow eating production. The agent's action cards appear at the timestep it acted, each with a one-sentence reason. A running euro counter diverges from the do-nothing ghost line. The audience watches money get saved in real time.

4. **Replay the failure moment.** The rule-based agent dispatches a repair crew at a weather bust, paying €500 for a truck roll that fixes nothing, because it cannot tell a cloud from a broken inverter. The LLM correctly re-trades instead. This is the drama beat, and it is reproducible, not hoped for.

5. **Close.** "Our scores are distributions, not anecdotes. We ran every agent through 500 versions of each bad day. Before August 12, run your worker through ours."

The gym wins even when our own agent loses. A mediocre LLM score is not a failed demo. It is the product argument: you need this measurement because agents are not as safe as they look.

---

## Feature walk: what we built and why the buyer cares

### 1. Physics-grounded simulation core
**What it is:** Every park is modeled with pvlib (the industry-standard PV physics library): real irradiance and temperature converted to AC power, 15-minute timesteps, a full day of 96 steps. The portfolio is three real locations (Zaragoza 50 MW, Valencia 40 MW, Munich 30 MW).

**Why the buyer cares:** This is the realism defense. When a domain expert pokes at the numbers, they trace back to real physics, not a toy curve we drew. The simulation is credible to the people whose job is to be skeptical of simulations.

### 2. Three bad-day scenarios that discriminate
**What it is:** Seeded, replayable, identical for every agent.
- **S1 cloud-front bust:** forecast says sunny, a front arrives 3 hours early. Correct move: re-trade the shortfall, do NOT send a crew.
- **S2 silent fault:** clear day, an inverter dies at 11:00 and silently kills 25% of a park. Correct move: dispatch a crew fast, re-trade the residual.
- **S3 eclipse day:** the August 12 finale. A perfectly forecastable obscuration on all three parks, plus an unforecastable cloud layer over Valencia, plus a price spike. Correct move: pre-trade the published curve early, react only to the cloud residual, no crew.

**Why the buyer cares:** S3 is the centerpiece because it mixes a knowable component with an unknowable one, which is exactly what separates a genuinely good agent from a lucky one. These are not random jitter. They are designed to expose the difference between agents that look fine and agents that are fine.

### 3. Honest, two-sided scoring (the oracle/floor bracket)
**What it is:** For every (scenario, agent) we compute three things. The **floor** is what doing nothing costs. The **oracle** is the scripted perfect response (the upper bound). The agent's score is *(floor cost − agent cost) / (floor cost − oracle cost)*, reported as **% of recoverable losses recovered**, clamped to [0, 1].

**Why the buyer cares:** This kills the "the scenario was just hard" objection dead. We are not scoring raw euros lost on a brutal day. We are scoring how much of the *recoverable* money the agent actually recovered, against a perfect player on the identical day. One currency, immune to gaming.

### 4. Safety flags, surfaced separately
**What it is:** False crew dispatches, trades against the gap direction, and steps-from-event-to-first-correct-action are tracked and shown as flags, not folded into the score.

**Why the buyer cares:** A high score with a safety violation is still a fail. The buyer sees *both* "it recovered 60% of losses" *and* "but it dispatched a crew that fixed nothing." That is the difference between a demo and an audit.

### 5. Monte Carlo robustness (scores are distributions, not anecdotes)
**What it is:** We run N=500 seeded variations of each scenario (front arrival jittered, fault onset and magnitude varied, cloud field randomized) and report mean recovery plus worst-decile (P10) tail risk per agent. Because each episode is just pvlib arithmetic, 500 runs cost seconds.

**Why the buyer cares:** This is the answer to the sharpest judge question: *"isn't this three hand-picked anecdotes?"* No. We scored the agent across the space of bad days and we can show you the worst 10% of outcomes, which is the number an asset owner actually cares about. The pitch line writes itself: "we ran every agent through 500 versions of each bad day."

### 6. The intelligent test-case generator (Test Lab)
**What it is:** Beyond the three hand-authored days, an evolutionary search generates a battery of bad days. Each test case is a parameter vector (weather busts, an optional silent fault, an eclipse overlay, a price regime). The search maximizes a fitness that rewards *recoverable money at stake* AND *how far the day separates a competent agent panel*, then diversity-selects a spread across failure modes. Two modes:
- **Discrimination:** agent-agnostic, find the days that separate good agents from bad.
- **Adversarial:** point the same search at one specific agent and mine its failures.

There is also an opt-in LLM **red-team author** that proposes novel cases as search seeds; every proposal still has to survive the fitness function.

**Why the buyer cares:** This is the moat and the upsell. We do not just grade against a fixed exam. We *manufacture* the hardest possible exam, on demand, and we can aim it at a specific agent. The sales line: *"pointed at your agent in adversarial mode, the generator drove its mean recovery from 49% down to 30%, surfacing exactly where it breaks before a customer asset does."* Finding the failure mode in our lab is worth far more than finding it on the grid.

### 7. Real data, not just synthetic (the SYNTHETIC / REAL DATA toggle)
**What it is:** One toggle in the UI switches the whole world between our deterministic synthetic scenarios and **real historical days**: Open-Meteo day-ahead forecasts versus archived actuals per park, plus real SMARD German day-ahead prices. S1's weather bust is a forecast error that genuinely happened.

**Why the buyer cares:** Skeptics assume a simulator is rigged. Flipping to REAL DATA and showing the same engine running on a real forecast bust against real market prices removes that doubt in one click. The forecast error is not ours. It is the market's.

### 8. Pluggable agent brains
**What it is:** Any agent is a Python class implementing one method: `act(obs) -> action`, where the action is `noop`, `trade`, or `dispatch_crew`. We ship a do-nothing floor, a deliberately naive rule-based agent, and an LLM worker. Real models (Claude via the Anthropic API, DeepSeek) enter the leaderboard as extra contestants. Crucially, **the numbers in the action cards come from the simulator, never from the LLM** (the model picks the action and writes the reason; the sim computes the euros).

**Why the buyer cares:** This is the framework-agnostic promise. The buyer's agent plugs into the same contract and gets scored on the same currency as everyone else. We are neutral infrastructure, not a competitor dressed as a judge. And because the euros are sim-computed, the LLM cannot flatter itself.

### 9. Episode replay UI (the trust-builder)
**What it is:** A time scrubber with a play button. The three-curve chart shows expected-from-forecast, expected-from-actual-weather, and actual production. A price strip runs underneath. Action cards appear at their timestep with the agent's reasoning. A running euro counter tracks the agent against the do-nothing ghost line.

**Why the buyer cares:** This is how you sell a number to a human. Instead of a spreadsheet that says "60% recovery," the buyer *watches* the agent notice the divergence, decide, act, and pull the euro line away from the ghost. Explainability is the difference between a score they distrust and a score they believe.

### 10. The Arena (live chaos injection + judge-plays-it)
**What it is:** A live mode where you inject chaos and the simulation re-runs instantly (it is fast pvlib arithmetic, so injections re-simulate on the spot). The judge-plays-it variant hands the three action buttons to the person in the room: they make the calls, their score lands on the leaderboard.

**Why the buyer cares:** Interactivity converts. When a prospect plays a bad day themselves, badly, and watches their score land below the LLM, they have *felt* the problem. They are no longer evaluating a pitch. They are recovering from losing to the machine, which is the moment they understand why the measurement matters.

### 11. Exportable certification reports (CSV + PDF)
**What it is:** The battery report is available as machine-readable CSV and a presentable PDF straight from the API: pass-rate, worst-case P10, and the single hardest day that breaks each agent.

**Why the buyer cares:** The certificate is the deliverable. The agent company drops the PDF into a sales proposal; the operator files the CSV for their audit trail. The artifact outlives the demo and travels through the buyer's organization to the people who sign.

### 12. Runs on a laptop, offline, deterministic
**What it is:** The whole demo runs from stored JSON traces with the network unplugged. Generation is deterministic given a seed. Tests run on a mock substrate with no API calls.

**Why the buyer cares:** No demo gods. Nothing live has to work in the room, so nothing can break in the room. Determinism also means the certificate is reproducible: anyone can re-run the exact battery and get the exact result, which is what "auditable" actually requires.

---

## The numbers (for the proposal)

The white-label pitch is a sales-accelerator argument, not a cost-saver. For an agent company like Invertix (stated 10 GW commercial pipeline):

- Certification attacks the #1 named blocker (trust) in the leakiest funnel stage (POC to production, where industry conversion sits under 50%).
- Base case: lifting conversion +12 pp on a 10 GW pipeline at ~€2.5M/GW/yr ARPU is **+1.2 GW converted, +€3.0M new ARR/yr (+30%)**.
- Gauntlet's fee at 5% of the certified book (~€13.0M) is **~€650K/yr**.
- That is roughly **€4.6 of new ARR for every €1 paid to Gauntlet**, before the other three levers (sales-cycle compression, price premium, catastrophe avoidance) stack on top.

Three revenue paths, one product:
1. **White-label certification** for agent companies (the scaler): annual platform fee + 5% of certified revenue, or €10K/agent flat with annual re-cert.
2. **SaaS subscription** for asset operators: tiered monthly, run your agents through the battery.
3. **Consulting** for large operators and regulators: custom stress scenarios built by the generator.

Year 1 target €500K to €1M (SaaS + consulting + first white-label pilot), scaling to €1M to €3.5M as 3 to 5 white-label accounts ramp.

---

## Objection handling

**"Isn't this just three cherry-picked bad days?"**
No. Monte Carlo runs 500 versions of each, and the generator manufactures a whole battery tuned to be hard and discriminating by construction. We report distributions and tail risk, not anecdotes.

**"Your simulator is rigged in your favor."**
Flip the toggle to REAL DATA. Same engine, real Open-Meteo forecasts, real SMARD prices, a forecast bust that genuinely happened. And the scoring brackets against a perfect oracle on the identical day, so "hard day" is not an excuse the score can hide behind.

**"You're an agent company grading your own homework."**
The agent contract is one method. Your agent plugs in and is scored on the same currency as ours. We are neutral. And our pitch survives our own agent losing, which no agent vendor's pitch can.

**"Eclipses are rare. Why should I care?"**
Iberia gets three solar eclipses in three years (total 2026, total 2027 over southern Spain, annular 2028). 2026 is the dress rehearsal for the bigger 2027 event. And the eclipse is just the marquee scenario; the same machinery stress-tests the cloud busts and silent faults that happen every week.

**"Why now?"**
The August 12 2026 eclipse is 8 weeks out and it is the only pre-scheduled continent-scale stress test on the grid. Every agent company wants to be able to say their worker is eclipse-ready. We are the only way to prove it.

---

## Honest assumptions (state these before you're asked)

Credibility comes from disclosing the model's edges, not hiding them:
- Imbalance price modeled at 2x the day-ahead proxy; intraday re-trade spread at ±10% of day-ahead.
- Single DE-LU price zone applied to the Spanish parks.
- Eclipse obscuration interpolated as a gaussian between published contact times (exact where it matters).
- The S3 evening price spike is our stated scenario assumption layered on top of real prices.
- Real-data settlement floors negative prices at 1 EUR/MWh to keep the oracle/floor bracket sound (displayed unfloored).

Saying these out loud is the evals company doing its job. It is the same instinct that makes the certificate worth trusting.
