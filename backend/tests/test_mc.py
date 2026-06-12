"""M8 gate (reduced n for test speed): distributions bounded and ordered."""

from gauntlet.run import run_mc


def test_mc_bounds_and_ordering(tmp_path):
    payload = run_mc("S1", 15, out=tmp_path)
    s = payload["summary"]
    for ag in ("noop", "rules", "llm"):
        assert 0.0 <= s[ag]["p10"] <= s[ag]["mean"] <= 1.0
    assert s["noop"]["mean"] == 0.0
    assert s["llm"]["mean"] > s["noop"]["mean"]
    assert s["llm"]["n"] == 15 and s["rules"]["n"] == 15
    assert (tmp_path / "mc_S1.json").exists()
