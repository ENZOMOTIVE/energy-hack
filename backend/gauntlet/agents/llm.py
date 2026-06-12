"""LLM worker with a deterministic mock fallback.

MockLLM (default): same trigger logic, scripted decisions using the gap
decomposition correctly. Offline and reproducible; used when no provider env
vars are set.

LLMWorker: identical triggers decide WHEN to call the model; the action
itself comes from the model as forced JSON. Supports two providers:
  - anthropic: uses the Anthropic SDK (ANTHROPIC_API_KEY)
  - deepseek: OpenAI-compatible (DEEPSEEK_API_KEY, base_url https://api.deepseek.com)

Select via GAUNTLET_PROVIDER=anthropic|deepseek.
Legacy: GAUNTLET_USE_ANTHROPIC=1 is equivalent to GAUNTLET_PROVIDER=anthropic.
"""

import json
import os
import time

import numpy as np

from .base import Action, Agent, Obs

PLANT_GAP_FRAC = 0.10  # of rated power, 2 consecutive steps -> fault
WEATHER_GAP_FRAC = 0.10  # of rated power on schedule-vs-twin -> trade trigger
TRADE_COOLDOWN_STEPS = 4
RESIDUAL_TRADE_HOURS = 2.0
WEATHER_TRADE_HOURS = 3.0
# selling surplus is asymmetrically risky: a vanished surplus becomes a 2x
# imbalance penalty, so sell short horizons and partial size only
SURPLUS_TRADE_HOURS = 1.0
SURPLUS_FRACTION = 0.8


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
            if gap_rem < -threshold and prev_gap < -threshold and cooldown_ok:
                return ("surplus", p, gap_rem)
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
        if kind == "surplus":
            self.state.last_trade_step[p] = k
            return Action(type="trade", park=p, delta_mw=-gap * SURPLUS_FRACTION,
                          hours=SURPLUS_TRADE_HOURS,
                          reason=(f"{p} is producing {-gap:.1f} MW above schedule: selling most "
                                  f"of the surplus short-term instead of giving it away"))
        self.state.last_trade_step[p] = k
        return Action(type="trade", park=p, delta_mw=-gap, hours=WEATHER_TRADE_HOURS,
                      reason=(f"Actual tracks weather-expected at {p}: forecast bust, not hardware. "
                              f"Buying back {gap:.1f} MW, no crew needed"))


SYSTEM_PROMPT = """You are an AI asset manager for a solar portfolio in a market simulation.
Each call you get one observation and must return exactly one JSON action, no other text.
Schema: {"action": "trade"|"dispatch_crew"|"noop", "park": "<id>", "delta_mw": <float>, "hours": <float>, "start_hour": <float or null>, "reason": "<one sentence>"}
Definitions: plant_gap = weather-expected minus actual (hardware problems). weather_gap = schedule minus weather-expected (forecast busts).
You are only called after a monitoring layer has verified a persistent anomaly (2+ steps) or a known event. Untreated gaps settle as imbalance at 2x price, so act now; noop is only correct if every gap is under 10% of that park's p_mw. Three cases:
1. plant_gap above 10% of p_mw: confirmed hardware fault. Dispatch crew for that park immediately, no further verification.
2. weather_gap above 10% of p_mw while plant_gap is near 0: confirmed forecast bust, weather only. Never dispatch crew; trade delta_mw = -(weather_gap_mw). Hours: 3 if recent_weather_gap holds one sign steadily, but only 1 if it oscillates between positive and negative (a volatile day makes long positions stale and costly).
3. weather_gap below -10% of p_mw: surplus. Sell it short: delta_mw = -(weather_gap_mw) * 0.8, hours exactly 1 (surpluses fade; an oversold position settles at 2x price).
Use numbers from the observation only.
Eclipse pre-trading: a solar_eclipse event lists tranches, each with start_hour (decimal, e.g. 19.25), hours and mean_lost_mw. When instructed to trade a tranche, take start_hour and hours from that tranche and set delta_mw = -(mean_lost_mw). Do NOT use the park's rated capacity. Do NOT leave start_hour null for future events."""

MAX_CALLS = 12
MIN_STEPS_BETWEEN_CALLS = 4

_PROVIDER_DEFAULTS = {
    "anthropic": "claude-sonnet-4-6",
    "deepseek": "deepseek-chat",
}


class LLMWorker(Agent):
    """Real-model LLM worker. Provider selected at init time."""

    def __init__(self, provider: str = "anthropic", model: str | None = None):
        self.provider = provider
        self.model = model or os.environ.get("GAUNTLET_MODEL") or _PROVIDER_DEFAULTS.get(provider, "deepseek-chat")
        self.name = provider  # trace file named after provider, e.g. S1_deepseek.json
        self.brain = self.model
        self._client = None
        self.state = _TriggerState()
        self.calls = 0
        self.last_call_step = -100
        self.step0_done = False
        self._queue: list[Action] = []

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        else:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com",
            )
        return self._client

    def act(self, obs: Obs) -> Action:
        if self._queue:
            return self._queue.pop(0)
        k = obs.step
        if k == 0 and obs.known_events and not self.step0_done:
            self.step0_done = True
            # one call per (park, tranche): the model can only emit one action per call
            jobs = []
            for ev in obs.known_events:
                if ev.get("type") != "solar_eclipse":
                    continue
                for ti, (_, _, lost) in enumerate(_eclipse_tranches(ev, obs.forecast[ev["park"]])):
                    if lost > 0.3:
                        jobs.append((ev["park"], ti))
            actions = []
            for p, ti in jobs:
                if self.calls >= MAX_CALLS:
                    break
                self.calls += 1
                payload = self._payload_focused(obs, focus_park=p, tranche=ti)
                actions.append(self._call_with_retry(payload, obs))
            self.last_call_step = k
            if not actions:
                return Action.noop()
            self._queue.extend(actions[1:])
            return actions[0]
        trig = self.state.update_and_check(obs)
        if trig is None or self.calls >= MAX_CALLS or k - self.last_call_step < MIN_STEPS_BETWEEN_CALLS:
            if trig is not None and trig[0] == "fault":
                self._rearm_fault(trig[1])  # trigger consumed but call gated: re-ask later
            return Action.noop()
        self.calls += 1
        self.last_call_step = k
        action = self._call_with_retry(self._payload(obs), obs)
        if trig[0] == "fault" and action.type != "dispatch_crew":
            self._rearm_fault(trig[1])  # model declined: keep the trigger alive
        return action

    def _rearm_fault(self, park: str):
        self.state.crew_sent.discard(park)
        self.state.pending_residual.discard(park)

    def _call_with_retry(self, payload: dict, obs: Obs) -> Action:
        delays = [1.0, 2.0]
        for attempt in range(3):
            try:
                text = self._complete(payload)
                return self._parse(text, obs)
            except Exception as exc:
                code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
                if code == 429 and attempt < 2:
                    time.sleep(delays[attempt])
                    continue
                break
        return Action.noop()

    def _complete(self, payload: dict) -> str:
        client = self._get_client()
        content = json.dumps(payload)
        # temperature 0: leaderboard traces must be as reproducible as the API allows
        if self.provider == "anthropic":
            msg = client.messages.create(
                model=self.model, max_tokens=300, temperature=0.0, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            return msg.content[0].text
        else:
            resp = client.chat.completions.create(
                model=self.model,
                max_tokens=300,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
            )
            return resp.choices[0].message.content

    def _payload_focused(self, obs: Obs, focus_park: str, tranche: int) -> dict:
        """Payload for a single (park, tranche) eclipse pre-trade decision."""
        payload = self._payload(obs)
        payload["known_events"] = [ev for ev in payload["known_events"] if ev.get("park") == focus_park]
        payload["instruction"] = (
            f"Pre-trade tranche index {tranche} of the eclipse at park {focus_park}. "
            f"Take start_hour, hours and mean_lost_mw from tranches[{tranche}] of the event; "
            f"delta_mw = -(mean_lost_mw)."
        )
        return payload

    def _payload(self, obs: Obs) -> dict:
        k = obs.step
        lo = max(0, k - 7)
        events = []
        for ev in obs.known_events:
            ev = dict(ev)
            if ev.get("type") == "solar_eclipse":
                # the obscuration is a gaussian: a flat mean trade over the window
                # over-buys the shoulders and under-buys the peak, so expose tranches
                ev["tranches"] = [
                    {"start_hour": round(start * 0.25, 2), "hours": round(n * 0.25, 2),
                     "mean_lost_mw": round(lost, 1)}
                    for start, n, lost in _eclipse_tranches(ev, obs.forecast[ev["park"]])
                ]
            events.append(ev)
        return {
            "step": k, "time": obs.time_iso,
            "parks": {
                p: {
                    "p_mw": obs.parks[p]["p_mw"],
                    "plant_gap_mw": round(float(obs.twin[p][k] - obs.actual[p][k]), 2),
                    "weather_gap_mw": round(float(obs.schedule[p][k] - obs.twin[p][k]), 2),
                    "recent_actual": [round(float(x), 1) for x in obs.actual[p][lo : k + 1]],
                    "recent_twin": [round(float(x), 1) for x in obs.twin[p][lo : k + 1]],
                    "recent_weather_gap": [round(float(obs.schedule[p][i] - obs.twin[p][i]), 1)
                                           for i in range(lo, k + 1)],
                    "schedule_now": round(float(obs.schedule[p][k]), 1),
                }
                for p in obs.forecast
            },
            "da_price_now": float(obs.da_price[k]),
            "da_price_next_3h": [float(x) for x in obs.da_price[k : min(96, k + 12)]],
            "known_events": events,
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
    """Returns MockLLM unless a real provider is configured."""
    provider = os.environ.get("GAUNTLET_PROVIDER", "")
    if not provider and os.environ.get("GAUNTLET_USE_ANTHROPIC") and os.environ.get("ANTHROPIC_API_KEY"):
        provider = "anthropic"
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return LLMWorker(provider="anthropic")
    if provider == "deepseek" and os.environ.get("DEEPSEEK_API_KEY"):
        return LLMWorker(provider="deepseek")
    return MockLLM()


def make_deepseek_agent() -> Agent:
    return LLMWorker(provider="deepseek")


def make_claude_agent() -> Agent:
    return LLMWorker(provider="anthropic")
