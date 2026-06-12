"""Agent contract: the gym calls act(obs) once per step and gets one Action back."""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Action:
    type: str = "noop"  # noop | trade | dispatch_crew
    park: str | None = None
    delta_mw: float = 0.0
    hours: float = 0.0
    start_step: int | None = None  # trades only; None means "starting next step"
    reason: str = ""

    @staticmethod
    def noop(reason: str = "") -> "Action":
        return Action(type="noop", reason=reason)


@dataclass
class Obs:
    step: int
    time_iso: str
    da_price: np.ndarray  # full 96
    parks: dict  # park_id -> {"p_mw": float}
    forecast: dict  # park_id -> full 96 (the day-ahead commitment basis)
    twin: dict  # park_id -> array up to and including current step
    actual: dict  # park_id -> array up to and including current step
    schedule: dict  # park_id -> full 96, current state after past trades
    known_events: list
    crew_dispatched: dict  # park_id -> bool


class Agent:
    name = "agent"
    brain = None  # set by LLM agents: "mock" | "anthropic"

    def act(self, obs: Obs) -> Action:  # pragma: no cover - interface
        raise NotImplementedError
