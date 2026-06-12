"""Arena backend: chaos injections and the human (scripted) agent."""

from fastapi.testclient import TestClient


def client():
    from gauntlet.api import app

    return TestClient(app)


def test_chaos_fault_gets_repaired_by_llm():
    # inject a midday fault on Munich into S1; the mock llm should see the plant
    # gap and dispatch a crew that is NOT a false dispatch
    r = client().post("/simulate", json={
        "scenario": "S1", "agent": "llm",
        "faults": [{"park": "munich", "step": 40, "magnitude": 0.5}],
    })
    assert r.status_code == 200
    body = r.json()
    crews = [a for a in body["actions"] if a["type"] == "dispatch_crew" and a["park"] == "munich"]
    assert crews and not crews[0]["false_dispatch"]
    assert 0.0 <= body["totals"]["score"] <= 1.0


def test_chaos_clouds_do_not_trigger_crew():
    r = client().post("/simulate", json={
        "scenario": "S2", "agent": "llm",
        "clouds": [{"park": "valencia", "start_step": 44, "end_step": 56, "depth": 0.3}],
    })
    assert r.status_code == 200
    body = r.json()
    crews = [a for a in body["actions"] if a["type"] == "dispatch_crew" and a["park"] == "valencia"]
    assert not crews, "clouds are weather: the llm must not send a crew"


def test_human_agent_scores():
    # judge dispatches the crew at the S2 fault onset step + trades the residual
    base = client().post("/simulate", json={"scenario": "S2", "agent": "noop"}).json()
    onset = next(k for k, s in enumerate(base["steps"])
                 if s["actual_mw"]["zaragoza"] < s["twin_mw"]["zaragoza"] - 0.5)
    r = client().post("/simulate", json={
        "scenario": "S2", "agent": "human",
        "human_actions": [
            {"k": onset + 1, "type": "dispatch_crew", "park": "zaragoza"},
            {"k": onset + 2, "type": "trade", "park": "zaragoza", "delta_mw": -8, "hours": 2},
        ],
    })
    body = r.json()
    assert body["agent"] == "human"
    assert body["totals"]["false_dispatches"] == 0
    assert body["totals"]["score"] > 0


def test_simulate_validation():
    assert client().post("/simulate", json={"scenario": "S9"}).status_code == 400
    assert client().post("/simulate", json={
        "scenario": "S1", "faults": [{"park": "atlantis", "step": 10}],
    }).status_code == 400
