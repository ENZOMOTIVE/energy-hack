"""RuleAgent: DELIBERATELY NAIVE. It never reads twin or known_events, so it
cannot tell a weather bust (or an eclipse) from a hardware fault. Its false
crew dispatches on S1 and S3 are an engineered demo beat (DEVPLAN section 6)."""

from .base import Action, Agent, Obs

BELOW_FRAC = 0.8
MIN_FORECAST_MW = 1.0
TRADE_HOURS = 4.0


class RuleAgent(Agent):
    name = "rules"

    def __init__(self):
        self.below_count = {}
        self.crew_sent = set()
        self.pending_trade = set()

    def act(self, obs: Obs) -> Action:
        for p in obs.forecast:
            k = obs.step
            fc = obs.forecast[p][k]
            ac = obs.actual[p][k]
            if fc > MIN_FORECAST_MW and ac < BELOW_FRAC * fc:
                self.below_count[p] = self.below_count.get(p, 0) + 1
            else:
                self.below_count[p] = 0

        # crew checks take priority over trades
        for p in obs.forecast:
            if self.below_count.get(p, 0) >= 2 and p not in self.crew_sent:
                self.crew_sent.add(p)
                self.pending_trade.add(p)
                return Action(type="dispatch_crew", park=p,
                              reason=f"{p} below 80% of forecast for 30 min, sending crew")

        for p in list(self.pending_trade):
            self.pending_trade.discard(p)
            k = obs.step
            gap = obs.forecast[p][k] - obs.actual[p][k]
            if gap > 0:
                return Action(type="trade", park=p, delta_mw=-gap, hours=TRADE_HOURS,
                              reason=f"covering {gap:.1f} MW shortfall at {p} for {TRADE_HOURS:.0f} h")
        return Action.noop()
