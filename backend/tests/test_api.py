"""M5 gate: API serves leaderboard and traces."""

from fastapi.testclient import TestClient


def test_api(tmp_path, monkeypatch):
    from gauntlet.api import app
    from gauntlet.run import run_all

    run_all(out=tmp_path)
    monkeypatch.setenv("GAUNTLET_TRACES_DIR", str(tmp_path))
    client = TestClient(app)

    r = client.get("/results")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 9

    r = client.get("/episodes/S3/llm")
    assert r.status_code == 200
    body = r.json()
    assert len(body["steps"]) == 96
    assert body["totals"]["score"] >= 0

    assert client.get("/episodes/S9/llm").status_code == 404
