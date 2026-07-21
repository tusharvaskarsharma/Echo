import asyncio

import app.workers.index_memory as index_module


def test_fallback_memory_indexing_preserves_retrieval_metadata(monkeypatch):
    upserts = []

    class FakeEmbeddings:
        def serialize_memory(self, memory):
            assert memory.content == "A story worth preserving"
            return memory.content

        async def embed_texts(self, texts):
            assert len(texts) == 1
            assert "Source evidence: A story worth preserving" in texts[0]
            return [[0.25, 0.75]]

    class FakePinecone:
        def upsert_vectors(self, namespace, vectors):
            upserts.append((namespace, vectors))

    monkeypatch.setattr("app.services.embedding_service.EmbeddingService", FakeEmbeddings)
    monkeypatch.setattr("app.services.pinecone_service.PineconeService", FakePinecone)
    payload = {
        "id": "memory-1", "session_id": "session-1", "subject_id": "user-1",
        "content": "A story worth preserving", "emotion_tags": ["reflection"],
        "topics": ["voice-session"], "people_mentioned": [], "time_period": None,
        "consent_level": "private", "confidence_score": 0.7,
    }

    asyncio.run(index_module._index_memory_async(payload, "user-1"))

    assert upserts[0][0] == "user-1"
    metadata = upserts[0][1][0]["metadata"]
    assert metadata["consent_level"] == "private"
    assert metadata["content"] == "A story worth preserving"
