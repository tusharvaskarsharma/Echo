import asyncio
import json

import pytest

from app.services.cognitive_engine import CognitiveEngineService


class FakeGroq:
    def __init__(self, payload): self.payload = payload
    async def complete(self, *_args, **_kwargs): return json.dumps(self.payload)


def low_confidence_plan(memory_id):
    return {
        "intent": "advice", "question_type": "personal advice", "required_memories": [memory_id], "required_traits": [],
        "missing_information": ["A repeated decision pattern"], "confidence": 0.4,
        "reasoning_plan": {"answer_strategy": "State uncertainty", "facts_to_use": [], "values_to_apply": [], "beliefs_to_apply": [], "personality_traits": [], "communication_style": "", "emotional_state": "", "important_relationships": [], "timeline_context": "", "possible_conflicts": [], "uncertainties": ["Only one memory"]},
        "response_constraints": {"should_answer": False, "should_refuse": False, "needs_more_context": True, "reason": "I don't know enough about this."},
        "citations": [memory_id], "system_prompt_for_persona_model": "Admit uncertainty. Do not reveal internal reasoning."
    }


def test_cognitive_engine_enforces_the_low_confidence_gate():
    service = CognitiveEngineService()
    service.groq = FakeGroq(low_confidence_plan("memory-1"))
    plan = asyncio.run(service.plan("What advice would they give?", [{"id": "memory-1", "content": "A short memory."}]))
    assert plan.response_constraints.should_answer is False


def test_cognitive_engine_rejects_unknown_citations():
    service = CognitiveEngineService()
    service.groq = FakeGroq(low_confidence_plan("unknown"))
    with pytest.raises(ValueError, match="unknown memory IDs"):
        asyncio.run(service.plan("What advice would they give?", [{"id": "memory-1", "content": "A short memory."}]))
