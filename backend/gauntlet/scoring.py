"""Score = share of recoverable losses recovered, bracketed by oracle and do-nothing."""


def score(agent_cost: float, floor_cost: float, oracle_cost: float) -> float:
    denom = floor_cost - oracle_cost
    if denom <= 0:
        return 0.0
    return float(min(1.0, max(0.0, (floor_cost - agent_cost) / denom)))
