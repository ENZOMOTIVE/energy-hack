"""Perfect-foresight cost, computed analytically (no search, no agent run).

The oracle matches its schedule to true actuals from step 0: every shortfall is
bought back at 1.1x instead of paying the 2.0x penalty, every surplus is sold at
0.9x. With a fault it dispatches the crew at onset, so the fault lasts exactly
REPAIR_STEPS, and it never false-dispatches.
"""

import numpy as np

from .config import BUYBACK_MULT, CREW_FEE_EUR, REPAIR_STEPS, SELLMORE_MULT, STEP_HOURS
from .scenarios import Scenario


def oracle_cost(scenario: Scenario) -> float:
    cost = 0.0
    fault = scenario.fault
    for p, forecast in scenario.forecast.items():
        actual = scenario.twin[p].copy()
        if fault and fault["park"] == p:
            onset = fault["onset_step"]
            end = min(len(actual), onset + REPAIR_STEPS)
            actual[onset:end] *= 1.0 - fault["magnitude"]
        gap = forecast - actual
        short = np.clip(gap, 0.0, None)
        surplus = np.clip(-gap, 0.0, None)
        cost += float(np.sum(short * STEP_HOURS * BUYBACK_MULT * scenario.da_price))
        cost -= float(np.sum(surplus * STEP_HOURS * SELLMORE_MULT * scenario.da_price))
    if fault:
        cost += CREW_FEE_EUR
    return cost
