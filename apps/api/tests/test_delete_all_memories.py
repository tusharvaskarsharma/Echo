import asyncio
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

import app.routers.memories as memory_router
from app.models.memory import DeleteAllMemoriesRequest


class FakeConnection:
    def __init__(self):
        self.fetch_calls = []
        self.execute_calls = []

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return [{"audio_url": "supabase://echo-session-audio/user-1/session-1/recording.webm"}]

    async def fetchrow(self, query, *args):
        self.fetch_calls.append((query, args))
        return {"memories": 3, "chunks": 8, "sessions": 2}

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))

    @asynccontextmanager
    async def transaction(self):
        yield self


def test_delete_all_memories_requires_exact_server_confirmation():
    with pytest.raises(HTTPException) as error:
        asyncio.run(memory_router.delete_all_memories(
            DeleteAllMemoriesRequest(confirmation="delete"), {"sub": "user-1"}, FakeConnection(),
        ))

    assert error.value.status_code == 400


def test_delete_all_memories_clears_only_the_authenticated_users_data(monkeypatch):
    calls = []

    class FakePinecone:
        def delete_vectors(self, namespace, **kwargs):
            calls.append(("pinecone", namespace, kwargs))

    class FakeAudioStorage:
        async def delete(self, storage_uri):
            calls.append(("audio", storage_uri))

    class FakeFallbackStorage:
        async def delete_all(self, user_id):
            calls.append(("fallback", user_id))

    monkeypatch.setattr(memory_router, "PineconeService", FakePinecone)
    monkeypatch.setattr(memory_router, "SessionAudioStorageService", FakeAudioStorage)
    monkeypatch.setattr(memory_router, "MemoryStorageService", FakeFallbackStorage)
    conn = FakeConnection()

    result = asyncio.run(memory_router.delete_all_memories(
        DeleteAllMemoriesRequest(confirmation="DELETE MY MEMORIES"), {"sub": "user-1"}, conn,
    ))

    assert result["deleted"] == {"memories": 3, "chunks": 8, "sessions": 2}
    assert ("pinecone", "user-1", {"delete_all": True}) in calls
    assert ("audio", "supabase://echo-session-audio/user-1/session-1/recording.webm") in calls
    assert ("fallback", "user-1") in calls
    assert len(conn.execute_calls) == 3
    for query, args in conn.execute_calls:
        assert "user_id = $1" in query
        assert args == ("user-1",)
