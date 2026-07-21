import asyncio
from types import SimpleNamespace
from uuid import uuid4

import app.routers.memories as memory_router
from app.models.memory import ConsentLevel, ConversationMemoryCreate, MemoryFragment


def test_conversation_save_uses_the_structured_session_processor_before_returning(monkeypatch):
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

    class FakeConnection:
        async def fetchrow(self, query, *args):
            assert "FROM public.memories" in query
            assert args[1] == user_id
            return {"id": "memory-1"}

    async def get_memory(_connection, memory_id, owner_id):
        assert memory_id == "memory-1" and owner_id == user_id
        return MemoryFragment(
            id="memory-1", session_id="session-1", subject_id=user_id,
            content="A conversation worth keeping.", emotion_tags=["reflective"], topics=["stories"],
            people_mentioned=[], consent_level=ConsentLevel.PRIVATE, confidence_score=0.8,
        )

    monkeypatch.setattr(memory_router, "SessionService", FakeSessionService)
    monkeypatch.setattr(memory_router.repositories, "get_memory", get_memory)

    saved = asyncio.run(
        memory_router.save_conversation_memory(
            ConversationMemoryCreate(content="A conversation worth keeping."),
            {"sub": user_id, "email": "person@example.com"},
            FakeConnection(),
        )
    )

    assert saved.content == "A conversation worth keeping."
