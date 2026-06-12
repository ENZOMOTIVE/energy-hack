from .base import Action, Agent, Obs


class DoNothingAgent(Agent):
    name = "noop"

    def act(self, obs: Obs) -> Action:
        return Action.noop()
