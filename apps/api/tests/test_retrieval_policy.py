import asyncio

import app.services.retrieval_service as retrieval_module
from app.services.retrieval_service import RetrievalService


def test_retrieval_enforces_owner_namespace_consent_and_threshold(monkeypatch):
    captured = {}

    class FakeEmbeddings:
        async def embed_texts(self, _texts):
            return [[0.1, 0.2]]

    class FakePinecone:
        def query(self, **kwargs):
            captured.update(kwargs)
            return [
                {"score": 0.91, "metadata": {"memory_id": "allowed", "content": "A consented memory"}},
                {"score": 0.71, "metadata": {"memory_id": "low", "content": "Too weak"}},
                {"score": 0.99, "metadata": {"memory_id": "empty"}},
            ]

    monkeypatch.setattr(retrieval_module, "EmbeddingService", FakeEmbeddings)
    monkeypatch.setattr(retrieval_module, "PineconeService", FakePinecone)

    result = asyncio.run(RetrievalService().retrieve_memories("What mattered?", "owner-1", ["family", "legacy"], min_score=0.8))

    assert [memory["memory_id"] for memory in result] == ["allowed"]
    assert captured["namespace"] == "owner-1"
    assert captured["top_k"] == 24
    assert captured["filter"]["owner_id"] == {"$eq": "owner-1"}
    assert captured["filter"]["consent_level"] == {"$in": ["family", "legacy"]}
