"""Real-data layer: only runs when data/real/ has been fetched. The synthetic
gates never depend on this, so CI/offline stays green without network."""

import numpy as np
import pytest
from gauntlet import realdata
from gauntlet.agents.noop import DoNothingAgent
from gauntlet.config import N_STEPS
from gauntlet.oracle import oracle_cost
from gauntlet.scenarios import build
from gauntlet.sim import run_episode

pytestmark = pytest.mark.skipif(not realdata.available(), reason="data/real not fetched")


def test_loader_shapes():
    for role in ("sunny", "cloudy"):
        d = realdata.load_role(role)
        assert d["prices"].shape == (N_STEPS,)
        for fc, ac in d["parks"].values():
            assert fc.shape == (N_STEPS,) and ac.shape == (N_STEPS,)
            assert fc.min() >= 0 and ac.min() >= 0


@pytest.mark.parametrize("name", ["S1", "S2", "S3"])
def test_real_bracket_holds(name):
    sc = build(name, data="real")
    assert sc.data == "real" and sc.day
    assert sc.settle_price is not None and sc.settle_price.min() >= 1.0
    floor = run_episode(sc, DoNothingAgent())["totals"]["cost_eur"]
    oracle = oracle_cost(sc)
    assert oracle < floor, f"{name} real: oracle {oracle} must beat floor {floor}"


def test_s1_real_has_a_real_bust():
    sc = build("S1", data="real")
    gap = sc.forecast["munich"] - sc.twin["munich"]
    assert gap.max() > 0.1 * 30.0, "chosen cloudy day must contain a real Munich bust"


def test_real_run_one(tmp_path):
    from gauntlet.run import run_one

    trace = run_one("S3", "llm", out=tmp_path, data="real")
    assert trace["data"] == "real"
    assert 0.0 <= trace["totals"]["score"] <= 1.0
    assert trace["totals"]["first_action_step"] == 0, "eclipse pre-trade must fire on real data too"
