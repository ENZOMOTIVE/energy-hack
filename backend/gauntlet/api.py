"""FastAPI app: two JSON endpoints plus static hosting of the built frontend."""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Gauntlet")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


def _traces_dir() -> Path:
    return Path(os.environ.get("GAUNTLET_TRACES_DIR", REPO_ROOT / "traces"))


@app.get("/results")
def results():
    f = _traces_dir() / "results.json"
    if not f.exists():
        raise HTTPException(404, "run `make traces` first")
    return json.loads(f.read_text())


@app.get("/episodes/{scenario}/{agent}")
def episode(scenario: str, agent: str):
    f = _traces_dir() / f"{scenario}_{agent}.json"
    if not f.exists():
        raise HTTPException(404, f"no trace for {scenario}/{agent}")
    return json.loads(f.read_text())


_dist = REPO_ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
