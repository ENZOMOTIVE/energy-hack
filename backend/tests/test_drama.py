"""M4 gate: the demo's drama beats, asserted. These ARE the pitch; if they fail,
tune thresholds or scenario magnitudes until they pass deterministically."""

import pytest
from gauntlet.run import run_one


@pytest.fixture(scope="module")
def traces(tmp_path_factory):
    out = tmp_path_factory.mktemp("traces")
    t = {}
    for sc in ("S1", "S2", "S3"):
        for ag in ("rules", "llm"):
            t[(sc, ag)] = run_one(sc, ag, out=out)
    return t


def test_s1_rules_false_dispatch_llm_clean(traces):
    assert traces[("S1", "rules")]["totals"]["false_dispatches"] >= 1
    assert traces[("S1", "llm")]["totals"]["false_dispatches"] == 0


def test_s3_rules_false_dispatch_llm_pretrades_at_step0(traces):
    assert traces[("S3", "rules")]["totals"]["false_dispatches"] >= 1
    assert traces[("S3", "llm")]["totals"]["false_dispatches"] == 0
    assert traces[("S3", "llm")]["totals"]["first_action_step"] == 0


def test_scores_bounded(traces):
    for trace in traces.values():
        assert 0.0 <= trace["totals"]["score"] <= 1.0


def test_llm_beats_rules_on_s1_and_s3(traces):
    for sc in ("S1", "S3"):
        llm = traces[(sc, "llm")]["totals"]["score"]
        rules = traces[(sc, "rules")]["totals"]["score"]
        assert llm > rules, f"{sc}: llm {llm} must beat rules {rules}"


def test_s2_both_dispatch_llm_at_least_as_fast(traces):
    for ag in ("rules", "llm"):
        dispatches = [a for a in traces[("S2", ag)]["actions"]
                      if a["type"] == "dispatch_crew" and not a["false_dispatch"]]
        assert dispatches, f"{ag} must dispatch the crew on S2"
    assert (traces[("S2", "llm")]["totals"]["steps_to_first_action"]
            <= traces[("S2", "rules")]["totals"]["steps_to_first_action"])
