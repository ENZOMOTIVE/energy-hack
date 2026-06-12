"""LLM worker with a deterministic mock fallback.

MockLLM (default): same trigger logic, scripted decisions using the gap
decomposition correctly. Used whenever GAUNTLET_USE_ANTHROPIC is unset or no
ANTHROPIC_API_KEY is present, so the whole demo runs offline and reproducibly.

LLMWorker: identical triggers decide WHEN to call the Anthropic API; the action
itself comes from the model as forced JSON. Numbers are clamped by the engine
and by this wrapper; reasons are the model's own words.
"""

import json
import os

import numpy as np

from .base import Action, Agent, Obs

PLANT_GAP_FRAC = 0.10  # of rated power, 2 consecutive steps -> fault
WEATHER_GAP_FRAC = 0.10  # of rated power on schedule-vs-twin -> trade trigger
TRADE_COOLDOWN_STEPS = 4
RESIDUAL_TRADE_HOURS = 2.0
WEATHER_TRADE_HOURS = 3.0


def _eclipse_tranches(event, forecast):
    """Two pre-trade tranches fitting the published obscuration curve: a flat
    cut over the whole window fits a gaussian badly and leaks money both ways."""
    ws, we = event["window_start_step"], event["window_end_step"]
    t_max, max_obs, sigma = event["t_max_min"], event["max_obscuration"], event["sigma_min"]
    ks = np.arange(ws, we + 1)
    t = ks * 15 + 7.5
    expected_lost = forecast[ws : we + 1] * max_obs * np.exp(-(((t - t_max) / sigma) ** 2))
    mid = len(ks) // 2
    return [
        (ws, mid, float(np.mean(expected_lost[:mid]))),
        (ws + mid, len(ks) - mid, float(np.mean(expected_lost[mid:]))),
    ]


class _TriggerState:
    def __init__(self):
        self.plant_count = {}
        self.crew_sent = set()
        self.pending_residual = set()
        self.last_trade_step = {}

    def update_and_check(self, obs: Obs):
        """Returns ("fault", park), ("residual", park), ("weather", park, gap) or None."""
        k = obs.step
        for p in obs.forecast:
            plant_gap = obs.twin[p][k] - obs.actual[p][k]
            if plant_gap > PLANT_GAP_FRAC * obs.parks[p]["p_mw"]:
                self.plant_count[p] = self.plant_count.get(p, 0) + 1
            else:
                self.plant_count[p] = 0
        for p in obs.forecast:
            if self.plant_count.get(p, 0) >= 2 and p not in self.crew_sent:
                self.crew_sent.add(p)
                self.pending_residual.add(p)
                return ("fault", p, 0.0)
        for p in list(self.pending_residual):
            self.pending_residual.discard(p)
            gap = obs.schedule[p][k] - obs.actual[p][k]
            if gap > 0:
                return ("residual", p, gap)
        for p in obs.forecast:
            gap_rem = obs.schedule[p][k] - obs.twin[p][k]
            prev_gap = obs.schedule[p][k - 1] - obs.twin[p][k - 1] if k > 0 else 0.0
            threshold = WEATHER_GAP_FRAC * obs.parks[p]["p_mw"]
            cooldown_ok = k - self.last_trade_step.get(p, -10) >= TRADE_COOLDOWN_STEPS
            if gap_rem > threshold and prev_gap > threshold and cooldown_ok:
                return ("weather", p, gap_rem)
        return None


class MockLLM(Agent):
    name = "llm"
    brain = "mock"

    def __init__(self):
        self.state = _TriggerState()
        self.queue = []

    def act(self, obs: Obs) -> Action:
        k = obs.step
        if k == 0 and obs.known_events:
            for ev in obs.known_events:
                p = ev["park"]
                for start, n_steps, lost_mw in _eclipse_tranches(ev, obs.forecast[p]):
                    if lost_mw > 0.3:
                        self.queue.append(Action(
                            type="trade", park=p, delta_mw=-lost_mw,
                            hours=n_steps * 0.25, start_step=start,
                            reason=(f"Known eclipse {ev['window']} at {p}: pre-selling back "
                                    f"{lost_mw:.1f} MW of obscured output before the imbalance market prices it"),
                        ))
        if self.queue:
            return self.queue.pop(0)

        trig = self.state.update_and_check(obs)
        if trig is None:
            return Action.noop()
        kind, p, gap = trig
        if kind == "fault":
            plant_gap = obs.twin[p][k] - obs.actual[p][k]
            weather_gap = obs.forecast[p][k] - obs.twin[p][k]
            return Action(type="dispatch_crew", park=p,
                          reason=(f"Plant gap {plant_gap:.1f} MW vs weather gap {weather_gap:.1f} MW at {p}: "
                                  f"this is hardware, dispatching crew"))
        if kind == "residual":
            self.state.last_trade_step[p] = k
            return Action(type="trade", park=p, delta_mw=-gap, hours=RESIDUAL_TRADE_HOURS,
                          reason=f"Covering {gap:.1f} MW residual at {p} until the crew repairs the fault")
        self.state.last_trade_step[p] = k
        return Action(type="trade", park=p, delta_mw=-gap, hours=WEATHER_TRADE_HOURS,
                      reason=(f"Actual tracks weather-expected at {p}: forecast bust, not hardware. "
                              f"Buying back {gap:.1f} MW, no crew needed"))


SYSTEM_PROMPT = """You are an AI asset manager for a solar portfolio in a market simulation.
Each call you get one observation and must return exactly one JSON action, no other text.
Schema: {"action": "trade"|"dispatch_crew"|"noop", "park": "<id>", "delta_mw": <float>, "hours": <float>, "start_hour": <float or null>, "reason": "<one sentence>"}
Rules: plant_gap = weather-expected minus actual (hardware problems). weather_gap = schedule minus weather-expected (forecast busts).
Dispatch crew ONLY for sustained plant_gap. Trade negative delta_mw to buy back shortfalls. Use numbers from the observation only.
A known future event (e.g. eclipse) should be pre-traded with start_hour at the event window."""

MAX_CALLS = 12
MIN_STEPS_BETWEEN_CALLS = 4


class LLMWorker(Agent):
    name = "llm"
    brain = "anthropic"

    def __init__(self, model: str | None = None):
        from anthropic import Anthropic

        self.client = Anthropic()
        self.model = model or os.environ.get("GAUNTLET_MODEL", "claude-sonnet-4-6")
        self.state = _TriggerState()
        self.calls = 0
        self.last_call_step = -100
        self.step0_done = False

    def act(self, obs: Obs) -> Action:
        k = obs.step
        should_call = False
        if k == 0 and obs.known_events and not self.step0_done:
            self.step0_done = True
            should_call = True
        elif self.state.update_and_check(obs) is not None:
            should_call = True
        if not should_call or self.calls >= MAX_CALLS or k - self.last_call_step < MIN_STEPS_BETWEEN_CALLS:
            return Action.noop()
        self.calls += 1
        self.last_call_step = k
        payload = self._payload(obs)
        for _ in range(2):
            try:
                msg = self.client.messages.create(
                    model=self.model, max_tokens=300, system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": json.dumps(payload)}],
                )
                return self._parse(msg.content[0].text, obs)
            except Exception:
                continue
        return Action.noop()

    def _payload(self, obs: Obs) -> dict:
        k = obs.step
        lo = max(0, k - 7)
        return {
            "step": k, "time": obs.time_iso,
            "parks": {
                p: {
                    "p_mw": obs.parks[p]["p_mw"],
                    "plant_gap_mw": round(float(obs.twin[p][k] - obs.actual[p][k]), 2),
                    "weather_gap_mw": round(float(obs.schedule[p][k] - obs.twin[p][k]), 2),
                    "recent_actual": [round(float(x), 1) for x in obs.actual[p][lo : k + 1]],
                    "recent_twin": [round(float(x), 1) for x in obs.twin[p][lo : k + 1]],
                    "schedule_now": round(float(obs.schedule[p][k]), 1),
                }
                for p in obs.forecast
            },
            "da_price_now": float(obs.da_price[k]),
            "da_price_next_3h": [float(x) for x in obs.da_price[k : min(96, k + 12)]],
            "known_events": obs.known_events,
            "crew_dispatched": obs.crew_dispatched,
        }

    def _parse(self, text: str, obs: Obs) -> Action:
        data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        act = data.get("action", "noop")
        if act == "noop":
            return Action.noop(reason=data.get("reason", ""))
        park = data.get("park")
        if park not in obs.forecast:
            return Action.noop()
        p_mw = obs.parks[park]["p_mw"]
        start = data.get("start_hour")
        return Action(
            type=act, park=park,
            delta_mw=float(np.clip(float(data.get("delta_mw", 0.0)), -p_mw, p_mw)),
            hours=float(np.clip(float(data.get("hours", 1.0)), 0.25, 12.0)),
            start_step=int(float(start) * 4) if start is not None else None,
            reason=str(data.get("reason", ""))[:300],
        )


def make_llm_agent() -> Agent:
    if os.environ.get("GAUNTLET_USE_ANTHROPIC") and os.environ.get("ANTHROPIC_API_KEY"):
        return LLMWorker()
    return MockLLM()
