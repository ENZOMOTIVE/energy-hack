"""Obscuration curves for the Aug 12 2026 eclipse.

Contact parameters come from published local circumstances (SPEC Appendix A);
the gaussian shape between contacts is a documented approximation.
"""

import numpy as np

from .config import N_STEPS

# park: (t_max minutes since midnight CEST, max obscuration, sigma minutes)
ECLIPSE_PARAMS = {
    "zaragoza": (20 * 60 + 29, 1.0, 25.0),
    "valencia": (20 * 60 + 30, 1.0, 25.0),
    "munich": (20 * 60 + 16, 0.888, 30.0),
}
WINDOW_START_MIN = 19 * 60 + 20  # 19:20
WINDOW_END_MIN = 21 * 60 + 10  # 21:10


def obscuration(park_id: str) -> np.ndarray:
    t_max, max_obs, sigma = ECLIPSE_PARAMS[park_id]
    obs = np.zeros(N_STEPS)
    for k in range(N_STEPS):
        t = k * 15 + 7.5
        if WINDOW_START_MIN <= t <= WINDOW_END_MIN:
            obs[k] = max_obs * np.exp(-(((t - t_max) / sigma) ** 2))
    return obs
