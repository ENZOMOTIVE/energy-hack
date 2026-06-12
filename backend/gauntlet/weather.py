"""Clear-sky irradiance and scenario cloud factors. The only pvlib usage is here."""

import numpy as np
import pandas as pd
from pvlib.location import Location

from .config import N_STEPS, PARKS, SIM_DATE, TZ

_cache: dict[str, np.ndarray] = {}


def timestamps() -> pd.DatetimeIndex:
    return pd.date_range(start=f"{SIM_DATE} 00:00", periods=N_STEPS, freq="15min", tz=TZ)


def clearsky_ghi(park_id: str) -> np.ndarray:
    if park_id not in _cache:
        p = PARKS[park_id]
        loc = Location(p["lat"], p["lon"], tz=TZ)
        ghi = loc.get_clearsky(timestamps(), model="ineichen")["ghi"].to_numpy()
        _cache[park_id] = ghi
    return _cache[park_id]


def ramp_window(start_min: float, end_min: float, depth: float, ramp_min: float = 30.0) -> np.ndarray:
    """Cloud factor array: 1.0 outside [start,end], `depth` inside, linear ramps on both edges.

    start_min/end_min are minutes since midnight; evaluated at step midpoints.
    """
    factor = np.ones(N_STEPS)
    for k in range(N_STEPS):
        t = k * 15 + 7.5
        if t <= start_min - ramp_min or t >= end_min + ramp_min:
            continue
        if t < start_min:
            frac = (t - (start_min - ramp_min)) / ramp_min
            factor[k] = 1.0 + frac * (depth - 1.0)
        elif t <= end_min:
            factor[k] = depth
        else:
            frac = (t - end_min) / ramp_min
            factor[k] = depth + frac * (1.0 - depth)
    return factor


def random_walk_factor(start_min: float, end_min: float, rng: np.random.Generator,
                       start_val: float = 0.9, sigma: float = 0.06,
                       lo: float = 0.55, hi: float = 1.0) -> np.ndarray:
    """Seeded random-walk cloud factor inside [start,end], 1.0 outside."""
    factor = np.ones(N_STEPS)
    val = start_val
    for k in range(N_STEPS):
        t = k * 15 + 7.5
        if start_min <= t < end_min:
            val = float(np.clip(val + rng.normal(0.0, sigma), lo, hi))
            factor[k] = val
    return factor
