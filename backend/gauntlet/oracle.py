"""Perfect-foresight cost, computed analytically (no search, no agent run).

The oracle matches its schedule to true actuals from step 0: every shortfall is
bought back at 1.1x instead of paying the 2.0x penalty, every surplus is sold at
0.9x. For each fault (scripted or chaos-injected) it dispatches the crew at
onset, so the fault lasts exactly REPAIR_STEPS, and it never false-dispatches.
"""

import numpy as np

from .config import BUYBACK_MULT, CREW_FEE_EUR, REPAIR_STEPS, SELLMORE_MULT, STEP_HOURS
from .scenarios import Scenario
from .sim import collect_faults


def oracle_cost(scenario: Scenario, injected_faults: list | None = None) -> float:
    cost = 0.0
    settle = scenario.settle_price if scenario.settle_price is not None else scenario.da_price
    faults = collect_faults(scenario, injected_faults)
    for p, forecast in scenario.forecast.items():
        actual = scenario.twin[p].copy()
        if p in faults:
            onset = faults[p]["onset_step"]
            end = min(len(actual), onset + REPAIR_STEPS)
            actual[onset:end] *= 1.0 - faults[p]["magnitude"]
        gap = forecast - actual
        short = np.clip(gap, 0.0, None)
        surplus = np.clip(-gap, 0.0, None)
        cost += float(np.sum(short * STEP_HOURS * BUYBACK_MULT * settle))
        cost -= float(np.sum(surplus * STEP_HOURS * SELLMORE_MULT * settle))
    cost += CREW_FEE_EUR * len(faults)
    return cost
