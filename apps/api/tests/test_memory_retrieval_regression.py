"""Regression coverage for the factual interview questions Echo must answer."""

import asyncio
from uuid import uuid4

import app.services.retrieval_service as retrieval_module
from app.models.memory import ConsentLevel, MemoryFragment
from app.services.memory_chunking import build_memory_chunks
from app.services.retrieval_service import RetrievalService


INTERVIEW = """
Echo: How did you meet your wife?
You: I met Neha through a mutual friend while working at a railway workshop.

Echo: What did your father and mother do?
You: My father was a school teacher. My mother stitched clothes for neighbors.

Echo: What lesson did your parents teach you?
You: They taught me character over success, honesty, and resilience.

Echo: What is your biggest regret and proudest moment?
You: I worked too much and missed my children's teenage years. I am proud that my daughter became a doctor and my son started a company.

Echo: What hobbies do you enjoy?
You: I enjoy gardening, fixing things, making tea, and listening to Kishore Kumar songs.

Echo: What do you hope your grandchildren remember about you?
You: I hope they remember kindness, being present, slow walks, butterflies, tea, and listening.

Echo: Why did you enjoy collecting seashells?
You: I loved collecting seashells with my father after storms because he said every shell had its own journey.

Echo: Who was Daniel?
You: Daniel was my older brother and the person who taught me to repair bicycles.

Echo: What made you love books?
You: My mother took me to the town library every Saturday, and books made the world feel bigger.
""".strip()


def _memory() -> MemoryFragment:
    return MemoryFragment(
        id=str(uuid4()), session_id=str(uuid4()), subject_id="owner-1", content=INTERVIEW,
        emotion_tags=["reflective"], topics=["interview"], people_mentioned=[],
        consent_level=ConsentLevel.PRIVATE, confidence_score=0.9,
    )


def test_chunking_keeps_an_echo_question_with_its_answer():
    chunks = build_memory_chunks(_memory())

    assert len(chunks) == 9
    assert "How did you meet your wife?" in chunks[0].content
    assert "mutual friend while working at a railway workshop" in chunks[0].content
    assert {chunk.category for chunk in chunks} >= {"Family", "Values", "Preferences", "Legacy"}


def test_interview_questions_retrieve_grounded_expected_evidence(monkeypatch):
    memory = _memory()
    chunks = build_memory_chunks(memory)
    vectors = [
        {
            "id": f"{memory.id}:chunk-{chunk.chunk_index}",
            "score": 0.42,
            "metadata": {
                "memory_id": str(memory.id), "chunk_index": chunk.chunk_index, "owner_id": "owner-1",
                "consent_level": "private", "content": chunk.content, "category": chunk.category,
                "keywords": chunk.keywords, "topics": memory.topics, "emotion_tags": memory.emotion_tags,
                "session_id": str(memory.session_id), "subject_id": "owner-1",
            },
        }
        for chunk in chunks
    ]

    class FakeEmbeddings:
        async def embed_texts(self, _texts):
            return [[0.1, 0.2]]

    class FakePinecone:
        def query(self, **_kwargs):
            return vectors

    monkeypatch.setattr(retrieval_module, "EmbeddingService", FakeEmbeddings)
    monkeypatch.setattr(retrieval_module, "PineconeService", FakePinecone)

    cases = {
        "How did you meet your wife?": "mutual friend while working at a railway workshop",
        "What did your father do?": "father was a school teacher",
        "What did your mother do?": "mother stitched clothes for neighbors",
        "What lesson did your parents teach you?": "character over success, honesty, and resilience",
        "What is your biggest regret?": "missed my children's teenage years",
        "What is your proudest moment?": "daughter became a doctor and my son started a company",
        "What hobbies do you enjoy?": "gardening, fixing things, making tea, and listening to kishore kumar songs",
        "What do you hope your grandchildren remember?": "kindness, being present, slow walks, butterflies, tea, and listening",
        "Why did you enjoy collecting seashells?": "collecting seashells with my father after storms",
        "Who was Daniel?": "daniel was my older brother",
        "What made you love books?": "mother took me to the town library every saturday",
    }
    for question, expected in cases.items():
        memories = asyncio.run(RetrievalService().retrieve_memories(
            question, "owner-1", ["private"], min_score=0.35,
        ))
        evidence = " ".join(item["content"].lower() for item in memories)
        assert expected in evidence, question
