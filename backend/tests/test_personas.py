"""Gates for the LLM worker personas and the genome failure-mode category.

All deterministic and offline: persona wiring assembles prompts and names
without touching the API (the client is lazy); category() is pure."""

from gauntlet.agents import personas
from gauntlet.agents.base import Action
from gauntlet.agents.llm import MAX_CALLS, LLMWorker, make_persona_agent
from gauntlet.genome import Bust, CaseGenome, Fault
from gauntlet.scenarios import build_from_genome
from gauntlet.sim import run_episode


def test_three_personas_registered():
    assert set(personas.PERSONA_IDS) == {"ds-cautious", "ds-balanced", "ds-aggressive"}
    for pid in personas.PERSONA_IDS:
        spec = personas.PERSONAS[pid]
        assert spec["label"] and spec["doctrine"] and spec["provider"] == "deepseek"


def test_persona_prompts_are_distinct():
    prompts = {pid: LLMWorker(provider="deepseek", persona=pid).system_prompt
               for pid in personas.PERSONA_IDS}
    # each persona's doctrine is appended, so all three system prompts differ
    assert len(set(prompts.values())) == 3
    # and each carries its own doctrine text
    assert "Cautious" in prompts["ds-cautious"]
    assert "Aggressive" in prompts["ds-aggressive"]


def test_persona_worker_identity():
    a = make_persona_agent("ds-cautious")
    assert a.name == "ds-cautious"          # trace file + leaderboard row id
    assert a.label == "Cautious"            # display label
    assert a.persona == "ds-cautious"
    # base worker (no persona) keeps the provider name and the bare prompt
    base = LLMWorker(provider="deepseek")
    assert base.name == "deepseek"
    assert base.system_prompt != a.system_prompt


def test_declined_fault_does_not_burn_the_call_budget():
    """A worker that keeps declining the crew on a persistent fault (the cautious
    'hedge a small fault and wait' path) must NOT re-trigger it every step and
    exhaust MAX_CALLS, which would starve every other park of model calls."""

    class DecliningWorker(LLMWorker):
        def __init__(self):
            super().__init__(provider="deepseek", persona="ds-cautious")

        def _call_with_retry(self, payload, obs):  # never hits the API
            park = next(iter(obs.forecast))
            return Action(type="trade", park=park, delta_mw=-1.0, hours=1.0, reason="stub decline")

    g = CaseGenome(fault=Fault("zaragoza", 36, 0.20))  # 20% fault, persists all day
    w = DecliningWorker()
    run_episode(build_from_genome(g, seed=0), w)
    assert w.calls <= 3 < MAX_CALLS  # bounded re-asks, not one per step


def test_category_classifies_failure_modes():
    fault_only = CaseGenome(fault=Fault("zaragoza", 48, 0.4))
    weather_only = CaseGenome(busts=[Bust("munich", 40, 60, 0.5, 1)])
    combo = CaseGenome(busts=[Bust("munich", 40, 60, 0.5, 1)], fault=Fault("zaragoza", 48, 0.4))
    eclipse = CaseGenome(busts=[Bust("munich", 40, 60, 0.5, 1)], eclipse=True)
    calm = CaseGenome()

    assert fault_only.category() == "FAULT"
    assert weather_only.category() == "WEATHER"
    assert combo.category() == "COMBO"
    assert eclipse.category() == "ECLIPSE"   # eclipse dominates even with a bust
    assert calm.category() == "CALM"
