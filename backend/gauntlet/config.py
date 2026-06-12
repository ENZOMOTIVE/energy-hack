"""Constants for the Gauntlet sim. Every number the rest of the code uses lives here."""

import numpy as np

PARKS = {
    "zaragoza": {"name": "Zaragoza ES", "p_mw": 50.0, "lat": 41.65, "lon": -0.88},
    "valencia": {"name": "Valencia ES", "p_mw": 40.0, "lat": 39.47, "lon": -0.38},
    "munich": {"name": "Munich DE", "p_mw": 30.0, "lat": 48.14, "lon": 11.58},
}
PARK_IDS = list(PARKS.keys())

PERF_RATIO = 0.90  # flat performance ratio, no temperature model
IMBALANCE_MULT = 2.0  # shortfall pays 2x DA per MWh
BUYBACK_MULT = 1.10  # reducing schedule buys back at 1.1x DA
SELLMORE_MULT = 0.90  # increasing schedule sells at 0.9x DA
CREW_FEE_EUR = 500.0
REPAIR_STEPS = 8  # crew fixes fault 8 steps (2 h) after dispatch

DEFAULT_SEED = 42
SIM_DATE = "2026-08-12"
TZ = "Etc/GMT-2"  # fixed UTC+2 (CEST); Etc zones have reversed signs
N_STEPS = 96
STEP_HOURS = 0.25

AGENTS = ["noop", "rules", "llm"]
SCENARIOS = ["S1", "S2", "S3"]

# day-ahead price by hour-of-day window: (start_hour, end_hour, EUR/MWh)
_PRICE_BLOCKS = [(0, 6, 55.0), (6, 9, 85.0), (9, 16, 45.0), (16, 19, 95.0), (19, 22, 130.0), (22, 24, 75.0)]


def da_price_curve(scenario: str) -> np.ndarray:
    prices = np.zeros(N_STEPS)
    for k in range(N_STEPS):
        h = k * STEP_HOURS
        for start, end, p in _PRICE_BLOCKS:
            if start <= h < end:
                prices[k] = p
                break
    if scenario == "S3":
        # stated assumption: eclipse evening spike
        for k in range(N_STEPS):
            if 19.5 <= k * STEP_HOURS < 21.0:
                prices[k] = 180.0
    return prices


def step_of(hour: float, minute: float = 0.0) -> int:
    """Step index whose interval contains the given wall-clock time."""
    return int((hour * 60 + minute) // 15)
