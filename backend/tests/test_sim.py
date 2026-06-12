"""M1 gate: engine economics on a hand-computed toy scenario."""

import numpy as np
from gauntlet.agents.base import Action, Agent
from gauntlet.agents.noop import DoNothingAgent
from gauntlet.config import N_STEPS
from gauntlet.scenarios import Scenario
from gauntlet.sim import run_episode


def toy_scenario(forecast_mw=10.0, actual_mw=8.0, n_active=4):
    forecast = np.zeros(N_STEPS)
    twin = np.zeros(N_STEPS)
    forecast[:n_active] = forecast_mw
    twin[:n_active] = actual_mw
    return Scenario(
        name="toy", seed=0, da_price=np.full(N_STEPS, 100.0),
        forecast={"zaragoza": forecast}, twin={"zaragoza": twin},
        fault=None, known_events=[], event_onset_step=0,
    )


def test_imbalance_hand_computed():
    # gap 2 MW * 0.25 h * 2.0 * 100 EUR = 100 EUR per step, 4 active steps
    trace = run_episode(toy_scenario(), DoNothingAgent())
    assert trace["steps"][0]["cum_cost_eur"] == 100.0
    assert trace["steps"][3]["cum_cost_eur"] == 400.0
    assert trace["steps"][95]["cum_cost_eur"] == 400.0


class TradeOnce(Agent):
    name = "trade_once"

    def act(self, obs):
        if obs.step == 0:
            return Action(type="trade", park="zaragoza", delta_mw=-2.0, hours=1.0)
        return Action.noop()


def test_trade_settlement():
    # step 0 settles before the trade applies: 100 EUR imbalance.
    # steps 1-3: schedule cut 10 -> 8, buyback 2 * 0.25 * 1.1 * 100 = 55 each.
    # step 4: forecast is 0, clip keeps schedule at 0, nothing charged.
    trace = run_episode(toy_scenario(), TradeOnce())
    assert trace["totals"]["cost_eur"] == 100.0 + 3 * 55.0


class FalseDispatch(Agent):
    name = "false_dispatch"

    def act(self, obs):
        if obs.step == 0:
            return Action(type="dispatch_crew", park="zaragoza")
        return Action.noop()


def test_false_dispatch_flagged():
    trace = run_episode(toy_scenario(), FalseDispatch())
    assert trace["totals"]["false_dispatches"] == 1
    assert trace["actions"][0]["false_dispatch"] is True
    assert trace["totals"]["cost_eur"] == 400.0 + 500.0
