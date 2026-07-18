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

    result = asyncio.run(RetrievalService().retrieve_memories("What mattered?", "subject-1", ["family", "legacy"]))

    assert result == [{"memory_id": "allowed", "content": "A consented memory"}]
    assert captured["namespace"] == "subject-1"
    assert captured["top_k"] == 12
    assert captured["filter"]["consent_level"] == {"$in": ["family", "legacy"]}
