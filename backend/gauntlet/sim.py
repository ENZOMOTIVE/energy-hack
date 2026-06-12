"""Episode engine and economics. One step = 15 minutes, 96 steps per episode.

Per-step order: compute actual production, let the agent act (trades affect
future steps only), then settle the current step's imbalance.
"""

import numpy as np

from .agents.base import Action, Agent, Obs
from .config import (BUYBACK_MULT, CREW_FEE_EUR, IMBALANCE_MULT, N_STEPS, PARKS,
                     REPAIR_STEPS, SELLMORE_MULT, STEP_HOURS)
from .scenarios import Scenario
from .weather import timestamps


def run_episode(scenario: Scenario, agent: Agent, floor_cum: np.ndarray | None = None) -> dict:
    times = timestamps()
    park_ids = list(scenario.forecast.keys())
    schedule = {p: scenario.forecast[p].copy() for p in park_ids}
    actual = {p: np.zeros(N_STEPS) for p in park_ids}
    crew_dispatched = {p: False for p in park_ids}
    repaired_at = N_STEPS + REPAIR_STEPS  # fault never repaired unless crew sent
    fault = scenario.fault

    cost = 0.0
    cum_cost = np.zeros(N_STEPS)
    false_dispatches = 0
    actions = []
    step_records = []

    for k in range(N_STEPS):
        for p in park_ids:
            a = scenario.twin[p][k]
            if fault and fault["park"] == p and fault["onset_step"] <= k < repaired_at:
                a *= 1.0 - fault["magnitude"]
            actual[p][k] = a

        obs = Obs(
            step=k, time_iso=times[k].isoformat(),
            da_price=scenario.da_price, parks={p: {"p_mw": PARKS[p]["p_mw"]} for p in park_ids},
            forecast={p: scenario.forecast[p] for p in park_ids},
            twin={p: scenario.twin[p][: k + 1] for p in park_ids},
            actual={p: actual[p][: k + 1] for p in park_ids},
            schedule={p: schedule[p].copy() for p in park_ids},
            known_events=scenario.known_events, crew_dispatched=dict(crew_dispatched),
        )
        action = agent.act(obs) or Action.noop()
        entry = None

        if action.type == "trade" and action.park in park_ids:
            p = action.park
            t0 = max(k + 1, action.start_step if action.start_step is not None else k + 1)
            t1 = min(N_STEPS, t0 + int(round(action.hours * 4)))
            for t in range(t0, t1):
                old = schedule[p][t]
                new = float(np.clip(old + action.delta_mw, 0.0, PARKS[p]["p_mw"]))
                applied = new - old
                if applied < 0:
                    cost += -applied * STEP_HOURS * BUYBACK_MULT * scenario.da_price[t]
                elif applied > 0:
                    cost -= applied * STEP_HOURS * SELLMORE_MULT * scenario.da_price[t]
                schedule[p][t] = new
            entry = {"k": k, "type": "trade", "park": p, "delta_mw": round(action.delta_mw, 2),
                     "hours": action.hours, "start_step": t0, "reason": action.reason,
                     "false_dispatch": False}

        elif action.type == "dispatch_crew" and action.park in park_ids:
            p = action.park
            cost += CREW_FEE_EUR
            is_false = False
            if not crew_dispatched[p]:
                crew_dispatched[p] = True
                fault_active = (fault and fault["park"] == p
                                and fault["onset_step"] <= k < repaired_at)
                if fault_active:
                    repaired_at = k + REPAIR_STEPS
                else:
                    false_dispatches += 1
                    is_false = True
            entry = {"k": k, "type": "dispatch_crew", "park": p, "delta_mw": 0.0,
                     "hours": 0.0, "start_step": None, "reason": action.reason,
                     "false_dispatch": is_false}

        if entry:
            actions.append(entry)

        for p in park_ids:
            gap = schedule[p][k] - actual[p][k]
            if gap > 0:
                cost += gap * STEP_HOURS * IMBALANCE_MULT * scenario.da_price[k]
        cum_cost[k] = cost

        step_records.append({
            "k": k, "time": times[k].isoformat(),
            "forecast_mw": {p: round(float(scenario.forecast[p][k]), 3) for p in park_ids},
            "twin_mw": {p: round(float(scenario.twin[p][k]), 3) for p in park_ids},
            "actual_mw": {p: round(float(actual[p][k]), 3) for p in park_ids},
            "schedule_mw": {p: round(float(schedule[p][k]), 3) for p in park_ids},
            "da_price": float(scenario.da_price[k]),
            "cum_cost_eur": round(float(cost), 2),
            "cum_cost_floor_eur": round(float(floor_cum[k]), 2) if floor_cum is not None else round(float(cost), 2),
            "action": actions[-1] if actions and actions[-1]["k"] == k else None,
        })

    first_after_onset = next((a["k"] for a in actions if a["k"] >= scenario.event_onset_step), None)
    return {
        "scenario": scenario.name, "agent": agent.name, "seed": scenario.seed,
        "parks": park_ids, "steps": step_records, "actions": actions,
        "totals": {
            "cost_eur": round(cost, 2),
            "false_dispatches": false_dispatches,
            "steps_to_first_action": (first_after_onset - scenario.event_onset_step)
            if first_after_onset is not None else -1,
            "first_action_step": actions[0]["k"] if actions else -1,
            **({"brain": agent.brain} if agent.brain else {}),
        },
        "_cum_cost": cum_cost,  # stripped before serialization
    }
