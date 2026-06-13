"""Gates for the LLM worker personas and the genome failure-mode category.

All deterministic and offline: persona wiring assembles prompts and names
without touching the API (the client is lazy); category() is pure."""

from gauntlet.agents import personas
from gauntlet.agents.llm import LLMWorker, make_persona_agent
from gauntlet.genome import Bust, CaseGenome, Fault


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
