"""Scenario construction: S1 cloudfront_bust, S2 silent_fault, S3 eclipse_day.

Each scenario yields per park: forecast_power (day-ahead basis), twin_power
(physics-expected from ACTUAL weather, never includes faults). The engine derives
actual power from twin plus fault state.
"""

from dataclasses import dataclass, field

import numpy as np

from . import eclipse, weather
from .config import DEFAULT_SEED, PARK_IDS, da_price_curve
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


def _clear_power(park_id: str) -> np.ndarray:
    return power_mw(park_id, weather.clearsky_ghi(park_id))


def build(name: str, seed: int = DEFAULT_SEED) -> Scenario:
    rng = np.random.default_rng(seed)
    if name == "S1":
        return _s1(rng, seed)
    if name == "S2":
        return _s2(rng, seed)
    if name == "S3":
        return _s3(rng, seed)
    raise ValueError(f"unknown scenario {name}")


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
    onset_min = 11 * 60 + rng.uniform(-120, 240)
    magnitude = rng.uniform(0.22, 0.40)
    forecast, twin = {}, {}
    for pid in PARK_IDS:
        clear = _clear_power(pid)
        forecast[pid] = clear
        twin[pid] = clear.copy()
    onset_step = int(onset_min // 15)
    return Scenario(
        name="S2", seed=seed, da_price=da_price_curve("S2"),
        forecast=forecast, twin=twin,
        fault={"park": "zaragoza", "onset_step": onset_step, "magnitude": float(magnitude)},
        known_events=[], event_onset_step=onset_step,
    )


def _s3(rng: np.random.Generator, seed: int) -> Scenario:
    """Eclipse on all parks plus uncertain clouds over Valencia.

    The day-ahead forecast EXCLUDES the obscuration and the clouds: the naive
    forecast pipeline missed the eclipse. Agents that read known_events win.
    """
    forecast, twin, events = {}, {}, []
    for pid in PARK_IDS:
        ghi = weather.clearsky_ghi(pid)
        forecast[pid] = power_mw(pid, ghi)
        factor = np.ones(len(ghi))
        if pid == "valencia":
            factor = weather.random_walk_factor(18 * 60, 21 * 60, rng)
        twin[pid] = power_mw(pid, ghi * factor * (1.0 - eclipse.obscuration(pid)))
        t_max_min, max_obs, sigma = eclipse.ECLIPSE_PARAMS[pid]
        events.append({
            "type": "solar_eclipse", "park": pid, "window": "19:20-21:10",
            "window_start_step": int(eclipse.WINDOW_START_MIN // 15),
            "window_end_step": int(eclipse.WINDOW_END_MIN // 15),
            "max_obscuration": max_obs, "t_max_min": t_max_min, "sigma_min": sigma,
        })
    return Scenario(
        name="S3", seed=seed, da_price=da_price_curve("S3"),
        forecast=forecast, twin=twin, fault=None, known_events=events,
        event_onset_step=int(eclipse.WINDOW_START_MIN // 15),
    )
