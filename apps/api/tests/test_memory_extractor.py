import json
import asyncio

from app.services.memory_extractor import MemoryExtractorService


VALID_MEMORY = {
    "title": "Planning a family hiking trip",
    "summary": (
        "The user discussed planning a hiking trip with their family. "
        "They said they prefer routes suitable for children and want to visit a national park."
    ),
    "context": "A planning conversation about a future family outdoor trip.",
    "important_facts": ["The user plans a hiking trip with family."],
    "user_preferences": ["The user prefers child-friendly hiking routes."],
    "people": ["family", "children"],
    "places": ["national park"],
    "topics": ["family travel", "hiking", "trip planning"],
    "keywords": [
        "family hiking", "hiking trip", "outdoor travel", "national park",
        "child-friendly routes", "children", "family vacation", "trail planning",
        "nature trip", "future travel",
    ],
    "emotion": {"primary": "excited", "confidence": 0.82},
    "intent": "planning",
    "memory_type": "goal",
    "importance_score": 0.72,
    "search_document": (
        "Planning a family hiking trip. The user plans a family hiking trip to a "
        "national park and prefers child-friendly hiking routes. This is a future "
        "family travel and outdoor planning goal. They felt excited about hiking, "
        "nature travel, trail planning, and a family vacation."
    ),
}


class FakeGroq:
    def __init__(self, response: dict):
        self.response = response

    async def complete(self, *_args, **_kwargs):
        return json.dumps(self.response)


def test_extractor_validates_and_maps_only_search_document_for_embedding():
    service = MemoryExtractorService()
    service.groq = FakeGroq(VALID_MEMORY)

    memories = asyncio.run(service.extract_memories([{"start": 0, "end": 3, "text": "We should take the children hiking."}]))

    assert len(memories) == 1
    memory = memories[0]
    assert memory.content == VALID_MEMORY["summary"]
    assert memory.search_document == VALID_MEMORY["search_document"]
    assert memory.semantic_metadata["important_facts"] == VALID_MEMORY["important_facts"]
    assert memory.emotion_tags == ["excited"]


def test_extractor_drops_invalid_provider_output_without_persisting_partial_memory():
    invalid = {**VALID_MEMORY, "topics": ["only one topic"]}
    service = MemoryExtractorService()
    service.groq = FakeGroq(invalid)

    assert asyncio.run(service.extract_memories([{"start": 0, "end": 1, "text": "hello"}])) == []
