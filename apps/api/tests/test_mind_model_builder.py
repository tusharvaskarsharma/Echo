import asyncio
import json

import pytest

from app.models.mind_model import StructuredMemoryInput
from app.services.mind_model_builder import MindModelBuilderService


class FakeGroq:
    def __init__(self, payload):
        self.payload = payload

    async def complete(self, *_args, **_kwargs):
        return json.dumps(self.payload)


def payload(memory_id: str):
    return {
        "identity": {"life_roles": [], "core_identity": [], "self_description": []},
        "values": [{"value": "Family connection", "confidence": 0.7, "evidence": [memory_id]}],
        "beliefs": [], "personality": [],
        "communication_style": {"tone": "", "humor": "", "formality": "", "empathy": "", "confidence": 0},
        "decision_patterns": [], "emotional_patterns": [], "life_lessons": [],
        "relationships": [], "interests": [], "goals": [], "uncertainties": [], "mind_summary": "",
    }


def test_builder_accepts_evidence_owned_by_the_input_memory():
    memory = StructuredMemoryInput(id="memory-1", content="I value time with my family.")
    service = MindModelBuilderService()
    service.groq = FakeGroq(payload(memory.id))
    model = asyncio.run(service.build([memory]))
    assert model.values[0].evidence == ["memory-1"]


def test_builder_rejects_unknown_evidence_ids():
    memory = StructuredMemoryInput(id="memory-1", content="I value time with my family.")
    service = MindModelBuilderService()
    service.groq = FakeGroq(payload("unknown-memory"))
    with pytest.raises(ValueError, match="unknown evidence IDs"):
        asyncio.run(service.build([memory]))
