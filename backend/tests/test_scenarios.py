"""M2 gate: scenario shapes with seed 42. M3 gate: oracle/floor bracket."""

import numpy as np
import pytest
from gauntlet import eclipse
from gauntlet.agents.noop import DoNothingAgent
from gauntlet.config import step_of
from gauntlet.oracle import oracle_cost
from gauntlet.scenarios import build
from gauntlet.sim import run_episode


def test_s1_shapes():
    sc = build("S1")
    lo, hi = step_of(14), step_of(18)
    fc, tw = sc.forecast["munich"], sc.twin["munich"]
    dip = [(tw[k] < 0.5 * fc[k]) and fc[k] > 1.0 for k in range(lo, hi)]
    assert any(dip), "Munich actual must dip below half of forecast in 14:00-18:00"
    assert np.allclose(sc.forecast["zaragoza"], sc.twin["zaragoza"])
    assert np.allclose(sc.forecast["valencia"], sc.twin["valencia"])
    assert sc.fault is None


def test_s2_shapes():
    sc = build("S2")
    for p in sc.forecast:
        assert np.allclose(sc.forecast[p], sc.twin[p]), "S2: twin equals forecast all day"
    assert sc.fault["park"] == "zaragoza"
    trace = run_episode(sc, DoNothingAgent())
    onset = sc.fault["onset_step"]
    actual = np.array([s["actual_mw"]["zaragoza"] for s in trace["steps"]])
    twin = np.array([s["twin_mw"]["zaragoza"] for s in trace["steps"]])
    assert np.all(actual[onset:] <= twin[onset:] + 1e-9)
    assert np.any(actual[onset:] < twin[onset:] - 0.5), "fault must bite"
    assert np.allclose(actual[:onset], twin[:onset])
    for p in ("valencia", "munich"):
        a = np.array([s["actual_mw"][p] for s in trace["steps"]])
        t = np.array([s["twin_mw"][p] for s in trace["steps"]])
        assert np.allclose(a, t)


def test_s3_shapes():
    sc = build("S3")
    ws, we = step_of(19, 20), step_of(21, 10)
    for p in sc.forecast:
        gap = sc.forecast[p] - sc.twin[p]
        in_window = gap[ws : we + 1]
        assert in_window.max() > 0, f"{p}: eclipse must create a forecast-twin gap"
        # peak of the relative dip sits at the park's published t_max (+/- 2 steps),
        # checked on the obscuration ratio where forecast is meaningful
        ratio = np.zeros_like(gap)
        mask = sc.forecast[p] > 0.5
        ratio[mask] = gap[mask] / sc.forecast[p][mask]
        peak_step = int(np.argmax(ratio))
        t_max_step = int(eclipse.ECLIPSE_PARAMS[p][0] // 15)
        assert abs(peak_step - t_max_step) <= 2, f"{p}: peak {peak_step} vs t_max {t_max_step}"
        # forecast itself has no dip: it is the clear-sky curve
        assert np.all(np.diff(sc.forecast[p][ws : we + 1]) <= 1e-6), \
            f"{p}: evening forecast should decline smoothly, no eclipse in it"
    assert len(sc.known_events) == 3


@pytest.mark.parametrize("name", ["S1", "S2", "S3"])
def test_oracle_strictly_beats_floor(name):
    sc = build(name)
    floor = run_episode(sc, DoNothingAgent())["totals"]["cost_eur"]
    oracle = oracle_cost(sc)
    assert oracle < floor, f"{name}: oracle {oracle} must be strictly below floor {floor}"


def test_noop_scores_zero(tmp_path):
    from gauntlet.run import run_one

    for name in ("S1", "S2", "S3"):
        trace = run_one(name, "noop", out=tmp_path)
        assert trace["totals"]["score"] == 0.0
