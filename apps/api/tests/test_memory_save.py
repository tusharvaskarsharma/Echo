import asyncio
from types import SimpleNamespace
from uuid import uuid4

import app.routers.memories as memory_router
from app.models.memory import ConversationMemoryCreate


def test_conversation_save_indexes_memory_before_returning(monkeypatch):
    user_id = str(uuid4())

    class FakeSessionService:
        def __init__(self, *_args):
            pass

        async def create_session(self, _request):
            return SimpleNamespace(id=uuid4(), subject_id=user_id)

        async def save_transcript(self, _session_id, transcript):
            assert transcript == "A conversation worth keeping."

        async def update_session(self, _session_id, _update):
            return None

    async def create_memory(_connection, memory, _owner_id):
        return memory

    indexed = []

    async def index_memory(payload, owner_id, **_kwargs):
        indexed.append((payload, owner_id))

    monkeypatch.setattr(memory_router, "SessionService", FakeSessionService)
    monkeypatch.setattr(memory_router.repositories, "create_memory", create_memory)
    monkeypatch.setattr(memory_router, "index_memory", index_memory)

    saved = asyncio.run(
        memory_router.save_conversation_memory(
            ConversationMemoryCreate(content="A conversation worth keeping."),
            {"sub": user_id, "email": "person@example.com"},
            object(),
        )
    )

    assert saved.content == "A conversation worth keeping."
    assert str(saved.subject_id) == user_id
    assert indexed[0][0]["id"] == str(saved.id)
    assert indexed[0][1] == user_id
