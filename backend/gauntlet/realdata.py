"""Loader for the real-data layer fetched by fetch_data.py. Disk only, no network.

Roles: "sunny" (base for S2/S3) and "cloudy" (real Munich forecast bust, S1).
Hourly inputs are expanded to the 96-step grid: prices as hourly step functions
(market reality), radiation linearly interpolated at step midpoints.
"""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .config import N_STEPS, PARK_IDS

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DIR = REPO_ROOT / "data" / "real"


def available() -> bool:
    return all((REAL_DIR / f).exists() for f in ("meta.json", "sunny.json", "cloudy.json"))


def meta() -> dict:
    return json.loads((REAL_DIR / "meta.json").read_text())


@lru_cache(maxsize=4)
def load_role(role: str) -> dict:
    if not available():
        raise FileNotFoundError(
            "real data missing: run `python -m gauntlet.fetch_data --auto` (network needed once)")
    d = json.loads((REAL_DIR / f"{role}.json").read_text())
    prices = np.repeat(np.array(d["prices_eur_mwh"], dtype=float), 4)
    step_mid_h = np.arange(N_STEPS) * 0.25 + 0.125
    hour_mid = np.arange(24) + 0.5
    parks = {}
    for pid in PARK_IDS:
        p = d["parks"][pid]
        fc = np.clip(np.interp(step_mid_h, hour_mid, np.array(p["forecast_ghi"], dtype=float)), 0.0, None)
        ac = np.clip(np.interp(step_mid_h, hour_mid, np.array(p["actual_ghi"], dtype=float)), 0.0, None)
        parks[pid] = (fc, ac)
    return {"day": d["day"], "prices": prices, "parks": parks}
