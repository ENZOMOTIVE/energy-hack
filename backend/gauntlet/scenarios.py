"""Scenario construction: S1 cloudfront_bust, S2 silent_fault, S3 eclipse_day.

Two data modes share the same scenario names and engine:
- synthetic (default): pvlib clear-sky + scripted weather. Deterministic
  substrate for all gating tests, MC, and the live arena.
- real: fetched Open-Meteo day-ahead forecasts vs archived actuals plus SMARD
  DE-LU prices (see fetch_data.py / realdata.py). S1's weather bust is a real
  forecast error that really happened; S2 keeps its scripted fault on a real
  sunny day; S3 overlays the computed eclipse on real weather.

Each scenario yields per park: forecast_power (day-ahead basis), twin_power
(physics-expected from ACTUAL weather, never includes faults). The engine
derives actual power from twin plus fault state.

Real days can have negative prices; settlement economics would invert the
oracle/floor bracket there, so settle_price floors at 1 EUR/MWh while da_price
keeps the real curve for display. Proper negative-price behavior (curtailment)
is on the TODO list.
"""

from dataclasses import dataclass

import numpy as np

from . import eclipse, realdata, weather
from .config import DEFAULT_SEED, PARK_IDS, PARKS, da_price_curve, step_of
from .parks import power_mw


@dataclass
class Scenario:
    name: str
    seed: int
    da_price: np.ndarray
    forecast: dict
    twin: dict
    fault: dict | None  # {"park", "onset_step", "magnitude"}
    known_events: list
    event_onset_step: int
    data: str = "synthetic"
    day: str | None = None  # real-data calendar day
    settle_price: np.ndarray | None = None  # economics price if it differs from display


def _clear_power(park_id: str) -> np.ndarray:
    return power_mw(park_id, weather.clearsky_ghi(park_id))


def build(name: str, seed: int = DEFAULT_SEED, data: str = "synthetic") -> Scenario:
    if data not in ("synthetic", "real"):
        raise ValueError(f"unknown data mode {data}")
    rng = np.random.default_rng(seed)
    builders = {
        ("S1", "synthetic"): _s1, ("S2", "synthetic"): _s2, ("S3", "synthetic"): _s3,
        ("S1", "real"): _s1_real, ("S2", "real"): _s2_real, ("S3", "real"): _s3_real,
    }
    if (name, data) not in builders:
        raise ValueError(f"unknown scenario {name}")
    return builders[(name, data)](rng, seed)


# ---------- synthetic ----------

def _s1(rng: np.random.Generator, seed: int) -> Scenario:
    """Cloud front over Munich arrives hours earlier than forecast. No fault."""
    forecast, twin = {}, {}
    actual_start_min = 14 * 60 + rng.uniform(-60, 60)
    for pid in PARK_IDS:
        clear = _clear_power(pid)
        if pid == "munich":
            ghi = weather.clearsky_ghi(pid)
            fc_factor = weather.ramp_window(17 * 60, 19 * 60, 0.40)
            ac_factor = weather.ramp_window(actual_start_min, 18 * 60 + 30, 0.35)
            forecast[pid] = power_mw(pid, ghi * fc_factor)
            twin[pid] = power_mw(pid, ghi * ac_factor)
        else:
            forecast[pid] = clear
            twin[pid] = clear.copy()
    return Scenario(
        name="S1", seed=seed, da_price=da_price_curve("S1"),
        forecast=forecast, twin=twin, fault=None, known_events=[],
        event_onset_step=int(actual_start_min // 15),
    )


def _s2(rng: np.random.Generator, seed: int) -> Scenario:
    """Clear day, forecast equals weather-true. Inverter fault on Zaragoza."""
    onset_step, magnitude = _fault_draw(rng)
    forecast, twin = {}, {}
    for pid in PARK_IDS:
        clear = _clear_power(pid)
        forecast[pid] = clear
        twin[pid] = clear.copy()
    return Scenario(
        name="S2", seed=seed, da_price=da_price_curve("S2"),
        forecast=forecast, twin=twin,
        fault={"park": "zaragoza", "onset_step": onset_step, "magnitude": magnitude},
        known_events=[], event_onset_step=onset_step,
    )


def _s3(rng: np.random.Generator, seed: int) -> Scenario:
    """Eclipse on all parks plus uncertain clouds over Valencia.

    The day-ahead forecast EXCLUDES the obscuration and the clouds: the naive
    forecast pipeline missed the eclipse. Agents that read known_events win.
    """
    forecast, twin = {}, {}
    for pid in PARK_IDS:
        ghi = weather.clearsky_ghi(pid)
        forecast[pid] = power_mw(pid, ghi)
        factor = np.ones(len(ghi))
        if pid == "valencia":
            factor = weather.random_walk_factor(18 * 60, 21 * 60, rng)
        twin[pid] = power_mw(pid, ghi * factor * (1.0 - eclipse.obscuration(pid)))
    return Scenario(
        name="S3", seed=seed, da_price=da_price_curve("S3"),
        forecast=forecast, twin=twin, fault=None, known_events=_eclipse_events(),
        event_onset_step=int(eclipse.WINDOW_START_MIN // 15),
    )


# ---------- real ----------

def _real_prices(role: str, spike: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """(display, settlement). Settlement floors at 1 EUR/MWh; S3 adds the
    stated eclipse-evening spike assumption on top of the real curve."""
    da = realdata.load_role(role)["prices"].copy()
    if spike:
        for k in range(96):
            if 19.5 <= k * 0.25 < 21.0:
                da[k] = max(da[k] * 1.5, 150.0)
    return da, np.maximum(da, 1.0)


def _real_powers(role: str) -> tuple[dict, dict, str]:
    d = realdata.load_role(role)
    forecast = {pid: power_mw(pid, d["parks"][pid][0]) for pid in PARK_IDS}
    twin = {pid: power_mw(pid, d["parks"][pid][1]) for pid in PARK_IDS}
    return forecast, twin, d["day"]


def _s1_real(rng: np.random.Generator, seed: int) -> Scenario:
    """The real Munich forecast bust, exactly as it happened. No script, no fault."""
    forecast, twin, day = _real_powers("cloudy")
    onset = step_of(12)
    gap = forecast["munich"] - twin["munich"]
    thr = 0.10 * PARKS["munich"]["p_mw"]
    for k in range(1, 95):
        if gap[k] > thr and gap[k + 1] > thr:
            onset = k
            break
    da, settle = _real_prices("cloudy")
    return Scenario(
        name="S1", seed=seed, da_price=da, forecast=forecast, twin=twin,
        fault=None, known_events=[], event_onset_step=onset,
        data="real", day=day, settle_price=settle,
    )


def _s2_real(rng: np.random.Generator, seed: int) -> Scenario:
    """Scripted Zaragoza fault (same seeded draw as synthetic) on a real sunny day."""
    onset_step, magnitude = _fault_draw(rng)
    forecast, twin, day = _real_powers("sunny")
    da, settle = _real_prices("sunny")
    return Scenario(
        name="S2", seed=seed, da_price=da, forecast=forecast, twin=twin,
        fault={"park": "zaragoza", "onset_step": onset_step, "magnitude": magnitude},
        known_events=[], event_onset_step=onset_step,
        data="real", day=day, settle_price=settle,
    )


def _s3_real(rng: np.random.Generator, seed: int) -> Scenario:
    """Computed eclipse overlaid on a real sunny day. Real clouds are already in
    the actuals, so the synthetic Valencia cloud walk is dropped. The day-ahead
    forecast still excludes the obscuration (the pipeline missed the eclipse)."""
    forecast, twin, day = _real_powers("sunny")
    twin = {pid: twin[pid] * (1.0 - eclipse.obscuration(pid)) for pid in PARK_IDS}
    da, settle = _real_prices("sunny", spike=True)
    return Scenario(
        name="S3", seed=seed, da_price=da, forecast=forecast, twin=twin,
        fault=None, known_events=_eclipse_events(),
        event_onset_step=int(eclipse.WINDOW_START_MIN // 15),
        data="real", day=day, settle_price=settle,
    )


# ---------- shared ----------

def _fault_draw(rng: np.random.Generator) -> tuple[int, float]:
    onset_min = 11 * 60 + rng.uniform(-120, 240)
    magnitude = rng.uniform(0.22, 0.40)
    return int(onset_min // 15), float(magnitude)


def _eclipse_events() -> list:
    events = []
    for pid in PARK_IDS:
        t_max_min, max_obs, sigma = eclipse.ECLIPSE_PARAMS[pid]
        events.append({
            "type": "solar_eclipse", "park": pid, "window": "19:20-21:10",
            "window_start_step": int(eclipse.WINDOW_START_MIN // 15),
            "window_end_step": int(eclipse.WINDOW_END_MIN // 15),
            "max_obscuration": max_obs, "t_max_min": t_max_min, "sigma_min": sigma,
        })
    return events
