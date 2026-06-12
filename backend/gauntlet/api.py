"""FastAPI app: leaderboard + trace endpoints, live /simulate for arena mode,
plus static hosting of the built frontend."""

import json
import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import realdata
from .agents.llm import LLMWorker
from .agents.scripted import ScriptedAgent
from .config import DEFAULT_SEED, N_STEPS, PARKS, SCENARIOS
from .oracle import oracle_cost
from .run import make_agent
from .scenarios import build
from .scoring import score
from .sim import run_episode
from .weather import ramp_window

REPO_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Gauntlet")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


def _traces_dir(data: str = "synthetic") -> Path:
    base = Path(os.environ.get("GAUNTLET_TRACES_DIR", REPO_ROOT / "traces"))
    return base / "real" if data == "real" else base


@app.get("/results")
def results(data: str = "synthetic"):
    f = _traces_dir(data) / "results.json"
    if not f.exists():
        raise HTTPException(404, f"no {data} traces yet: run `make traces`"
                            + ("-real" if data == "real" else ""))
    return json.loads(f.read_text())


@app.get("/episodes/{scenario}/{agent}")
def episode(scenario: str, agent: str, data: str = "synthetic"):
    f = _traces_dir(data) / f"{scenario}_{agent}.json"
    if not f.exists():
        raise HTTPException(404, f"no {data} trace for {scenario}/{agent}")
    return json.loads(f.read_text())


class ChaosFault(BaseModel):
    park: str
    step: int = Field(ge=0, le=N_STEPS - 1)
    magnitude: float = Field(default=0.35, ge=0.05, le=0.9)


class ChaosClouds(BaseModel):
    park: str
    start_step: int = Field(ge=0, le=N_STEPS - 1)
    end_step: int = Field(ge=0, le=N_STEPS - 1)
    depth: float = Field(default=0.4, ge=0.1, le=1.0)


class HumanAction(BaseModel):
    k: int = Field(ge=0, le=N_STEPS - 1)
    type: str  # trade | dispatch_crew
    park: str
    delta_mw: float = 0.0
    hours: float = 2.0


class SimRequest(BaseModel):
    scenario: str
    agent: str = "llm"  # noop | rules | llm | human
    seed: int = DEFAULT_SEED
    data: str = "synthetic"
    faults: list[ChaosFault] = []
    clouds: list[ChaosClouds] = []
    human_actions: list[HumanAction] = []


@app.post("/simulate")
def simulate(req: SimRequest):
    """Live arena episode: canonical scenario + chaos injections, re-scored on the fly.

    Deterministic given the same request, finishes in milliseconds (mock brain only)."""
    if req.scenario not in SCENARIOS:
        raise HTTPException(400, f"unknown scenario {req.scenario}")
    if req.data not in ("synthetic", "real"):
        raise HTTPException(400, f"unknown data mode {req.data}")
    if req.data == "real" and not realdata.available():
        raise HTTPException(400, "real data missing: run `python -m gauntlet.fetch_data --auto`")
    for item in [*req.faults, *req.clouds]:
        if item.park not in PARKS:
            raise HTTPException(400, f"unknown park {item.park}")

    scenario = build(req.scenario, req.seed, data=req.data)
    for c in req.clouds:  # chaos clouds are weather: they belong in twin (and actual)
        lo, hi = sorted((c.start_step, c.end_step))
        factor = ramp_window(lo * 15, hi * 15, c.depth, ramp_min=15.0)
        scenario.twin[c.park] = scenario.twin[c.park] * factor
    injected = [{"park": f.park, "onset_step": f.step, "magnitude": f.magnitude} for f in req.faults]

    if req.agent == "human":
        agent = ScriptedAgent([a.model_dump() for a in req.human_actions])
    else:
        try:
            agent = make_agent(req.agent)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if isinstance(agent, LLMWorker):
            raise HTTPException(400, "live simulate runs the mock brain only; use precomputed traces for real LLMs")

    from .agents.noop import DoNothingAgent

    floor_trace = run_episode(scenario, DoNothingAgent(), injected_faults=injected)
    floor_cum = floor_trace["_cum_cost"]
    trace = run_episode(scenario, agent, floor_cum=floor_cum, injected_faults=injected)
    floor = float(floor_cum[-1])
    oracle = oracle_cost(scenario, injected_faults=injected)
    trace["totals"]["floor_eur"] = round(floor, 2)
    trace["totals"]["oracle_eur"] = round(oracle, 2)
    trace["totals"]["score"] = round(score(trace["totals"]["cost_eur"], floor, oracle), 4)
    trace["data"] = req.data
    trace["day"] = scenario.day
    trace.pop("_cum_cost", None)
    return trace


_dist = REPO_ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
