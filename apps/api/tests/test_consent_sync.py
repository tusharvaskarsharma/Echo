"""Offline contract test for owner-scoped Pinecone consent updates."""

import asyncio
from contextlib import asynccontextmanager

from app.db.client import db_client
from app.models.memory import ConsentLevel, MemoryFragment
from app.workers import sync_consent


class FakePool:
    @asynccontextmanager
    async def acquire(self):
        yield object()


def test_consent_worker_uses_database_owner_and_subject_namespace(monkeypatch):
    memory = MemoryFragment(
        id="memory-123", session_id="session-123", subject_id="subject-123",
        content="A private family memory", emotion_tags=[], topics=[], people_mentioned=[],
        consent_level=ConsentLevel.LEGACY, confidence_score=0.8,
    )
    calls = []

    async def fake_get_memory(_conn, memory_id, user_id):
        assert memory_id == "memory-123"
        assert user_id == "owner-123"
        return memory

    class FakePinecone:
        def update_metadata(self, namespace, vector_id, metadata):
            calls.append((namespace, vector_id, metadata))

    monkeypatch.setattr(db_client, "pool", FakePool())
    monkeypatch.setattr(sync_consent.repositories, "get_memory", fake_get_memory)
    monkeypatch.setattr("app.services.pinecone_service.PineconeService", FakePinecone)

    asyncio.run(sync_consent._sync_memory_consent_async("memory-123", "owner-123"))

    assert calls == [("subject-123", "memory-123", {"consent_level": "legacy"})]
