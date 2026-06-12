"""PV power model. Deliberately minimal: flat performance ratio, no temperature model."""

import numpy as np

from .config import PARKS, PERF_RATIO


def power_mw(park_id: str, ghi_eff: np.ndarray) -> np.ndarray:
    p_mw = PARKS[park_id]["p_mw"]
    return np.clip(p_mw * (ghi_eff / 1000.0) * PERF_RATIO, 0.0, p_mw)
