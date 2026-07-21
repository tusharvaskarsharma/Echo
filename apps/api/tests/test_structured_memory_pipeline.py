import asyncio
from uuid import uuid4

import app.services.retrieval_service as retrieval_module
from app.models.memory import ConsentLevel, MemoryFragment
from app.services.memory_chunking import build_memory_chunks, build_story_units
from app.services.persona_service import PersonaService
from app.services.retrieval_service import RetrievalService


TRANSCRIPT = """Echo: How did you meet your wife?
You: I met Neha through a mutual friend while working at a railway workshop.

Echo: What lesson did your parents teach you?
You: They taught me character over success, honesty, and resilience."""


def test_ingestion_creates_one_complete_structured_memory_per_interview_exchange():
    units = build_story_units(TRANSCRIPT)

    assert len(units) == 2
    assert units[0].title == "How did you meet your wife"
    assert units[0].category == "Relationships"
    assert "mutual friend while working at a railway workshop" in units[0].content
    assert units[1].category == "Values"
    assert units[1].importance_score >= 0.9


def test_embedding_text_contains_summary_metadata_and_complete_evidence():
    unit = build_story_units(TRANSCRIPT)[0]
    memory = MemoryFragment(
        id=str(uuid4()), session_id=str(uuid4()), subject_id="owner-1", content=unit.content,
        emotion_tags=["reflective"], topics=["relationships"], people_mentioned=["Neha"],
        consent_level=ConsentLevel.PRIVATE, confidence_score=0.9,
        semantic_metadata={
            "title": unit.title, "summary": unit.summary, "category": unit.category,
            "keywords": unit.keywords, "importance_score": unit.importance_score,
        },
    )

    chunk = build_memory_chunks(memory)[0]

    assert "Title: How did you meet your wife" in chunk.search_text
    assert "Category: Relationships" in chunk.search_text
    assert "Source evidence:" in chunk.search_text
    assert "railway workshop" in chunk.search_text


def test_metadata_reranking_prefers_the_matching_person_over_equal_semantic_scores(monkeypatch):
    class FakeEmbeddings:
        async def embed_texts(self, _texts):
            return [[0.1, 0.2]]

    class FakePinecone:
        def query(self, **_kwargs):
            return [
                {"id": "father", "score": 0.45, "metadata": {
                    "memory_id": "father", "content": "A preserved family memory.", "category": "Family",
                    "people": ["father"], "title": "Father's work", "importance_score": 0.96,
                }},
                {"id": "hobby", "score": 0.45, "metadata": {
                    "memory_id": "hobby", "content": "A preserved preference memory.", "category": "Preferences",
                    "people": [], "title": "Gardening", "importance_score": 0.66,
                }},
            ]

    monkeypatch.setattr(retrieval_module, "EmbeddingService", FakeEmbeddings)
    monkeypatch.setattr(retrieval_module, "PineconeService", FakePinecone)

    results = asyncio.run(RetrievalService().retrieve_memories(
        "What did your father do?", "owner-1", ["private"], min_score=0.35,
    ))

    assert results[0]["memory_id"] == "father"
    assert results[0]["metadata_score"] > results[1]["metadata_score"]


def test_retrieval_expands_links_after_direct_evidence_without_crossing_owner_boundary(monkeypatch):
    class FakeEmbeddings:
        async def embed_texts(self, _texts):
            return [[0.1, 0.2]]

    class FakePinecone:
        def query(self, **_kwargs):
            return [{"id": "father", "score": 0.9, "metadata": {
                "memory_id": "father", "content": "My father was a teacher.", "category": "Family",
                "related_memory_ids": ["lesson"], "importance_score": 0.96,
            }}]

    class FakeConnection:
        async def fetch(self, query, *args):
            if "c.memory_id::text" not in query:
                return []
            assert args[0] == "owner-1"
            assert args[1] == ["private"]
            assert args[2] == ["lesson"]
            return [{
                "embedding_id": "lesson:chunk-0", "memory_id": "lesson", "chunk_index": 0,
                "category": "Values", "content": "He taught me honesty.", "keywords": ["honesty"],
                "session_id": "session-1", "subject_id": "owner-1", "consent_level": "private",
                "emotion_tags": [], "topics": ["values"], "people_mentioned": ["father"],
                "time_period": None, "confidence_score": 0.9, "search_document": "Father taught honesty.",
                "semantic_metadata": {"importance_score": 0.94, "category": "Values"},
            }]

    monkeypatch.setattr(retrieval_module, "EmbeddingService", FakeEmbeddings)
    monkeypatch.setattr(retrieval_module, "PineconeService", FakePinecone)
    service = RetrievalService()

    async def skip_legacy_reindex(*_args, **_kwargs):
        return None

    monkeypatch.setattr(service, "_ensure_legacy_index", skip_legacy_reindex)
    results = asyncio.run(service.retrieve_memories(
        "Tell me about your father", "owner-1", ["private"], conn=FakeConnection(), top_k=2,
    ))

    assert [item["memory_id"] for item in results] == ["father", "lesson"]
    assert results[1]["related_score"] == 0.15


def test_keyword_retrieval_remains_usable_when_embeddings_are_unavailable(monkeypatch):
    class BrokenEmbeddings:
        async def embed_texts(self, _texts):
            raise RuntimeError("embedding provider unavailable")

    class FakeConnection:
        async def fetch(self, _query, *_args):
            return [{
                "embedding_id": "father:chunk-0", "memory_id": "father", "chunk_index": 0,
                "category": "Family", "content": "My father was a school teacher.", "keywords": ["father", "teacher"],
                "session_id": "session-1", "subject_id": "owner-1", "consent_level": "private",
                "emotion_tags": [], "topics": ["family"], "people_mentioned": ["father"],
                "time_period": None, "confidence_score": 0.9, "search_document": "Father was a school teacher.",
                "semantic_metadata": {"title": "Father's work", "summary": "Father was a school teacher.", "importance_score": 0.96},
                "database_keyword_rank": 0.8,
            }]

    monkeypatch.setattr(retrieval_module, "EmbeddingService", BrokenEmbeddings)
    service = RetrievalService()

    async def skip_legacy_reindex(*_args, **_kwargs):
        return None

    monkeypatch.setattr(service, "_ensure_legacy_index", skip_legacy_reindex)
    results = asyncio.run(service.retrieve_memories(
        "What did your father do?", "owner-1", ["private"], conn=FakeConnection(),
    ))

    assert results[0]["memory_id"] == "father"
    assert results[0]["keyword_score"] > 0


def test_prompt_uses_structured_memories_before_the_grounding_rules():
    prompt = PersonaService().build_prompt("Test", {"style": "Warm"}, [{
        "content": "I met Neha through a mutual friend.", "category": "Relationships",
        "title": "Meeting Neha", "summary": "Met Neha through a mutual friend.",
        "people": ["Neha"], "semantic_metadata": {"important_facts": ["Met Neha through a mutual friend."]},
    }])

    assert prompt.index("=== RETRIEVED MEMORIES ===") < prompt.index("=== GROUNDING RULES ===")
    assert "Meeting Neha" in prompt
