"""Judge-plays-it: replays human decisions captured by the UI, one per step."""

from .base import Action, Agent, Obs


class ScriptedAgent(Agent):
    name = "human"

    def __init__(self, actions: list[dict]):
        self.by_step = {int(a["k"]): a for a in actions}  # last action per step wins

    def act(self, obs: Obs) -> Action:
        a = self.by_step.get(obs.step)
        if not a:
            return Action.noop()
        return Action(
            type=a["type"], park=a.get("park"),
            delta_mw=float(a.get("delta_mw", 0.0)), hours=float(a.get("hours", 2.0)),
            reason="judge decision",
        )
