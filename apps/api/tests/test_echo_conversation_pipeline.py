"""Conversation endpoint failure classification and planner fallback coverage."""

import asyncio

import pytest
from fastapi import HTTPException

import app.routers.echo_conversation as echo_module
from app.routers.echo_conversation import EchoConversationRequest, conversation
from app.services.groq_service import GroqUnavailableError


class FakeConnection:
    def __init__(self, *, memories=1, chunks=1, indexed=1):
        self.memories, self.chunks, self.indexed = memories, chunks, indexed

    async def fetchrow(self, query, *_args):
        if "FROM subjects" in query:
            return {"id": "owner-1", "user_id": "owner-1", "full_name": "Test"}
        if "memory_count" in query:
            return {"memory_count": self.memories, "chunk_count": self.chunks, "indexed_chunk_count": self.indexed}
        if "mind_model_snapshots" in query:
            return None
        if "SELECT m.content" in query:
            return {"content": "Met Neha through a mutual friend.", "session_id": "session-1", "occurred_at": None}
        raise AssertionError(query)


def _retrieved_memory():
    return {
        "memory_id": "memory-1", "content": "I met Neha through a mutual friend while working at a railway workshop.",
        "emotion_tags": ["reflective"], "topics": ["wife"], "session_id": "session-1",
        "retrieval_score": 0.85,
    }


def test_malformed_cognitive_plan_falls_back_to_final_grounded_generation(monkeypatch):
    class FakeRetrieval:
        async def retrieve_memories(self, *_args, **_kwargs):
            return [_retrieved_memory()]

    class FailingPlanner:
        async def plan(self, *_args, **_kwargs):
            raise ValueError("planner JSON violates schema")

    class FakeGroq:
        async def complete(self, messages, **_kwargs):
            assert messages[-1]["content"] == "How did I meet my wife?"
            return "You met Neha through a mutual friend while working at a railway workshop."

    monkeypatch.setattr(echo_module, "RetrievalService", FakeRetrieval)
    monkeypatch.setattr(echo_module, "CognitiveEngineService", FailingPlanner)
    monkeypatch.setattr(echo_module, "GroqService", FakeGroq)

    response = asyncio.run(conversation(
        EchoConversationRequest(question="How did I meet my wife?"),
        {"sub": "owner-1"}, FakeConnection(),
    ))

    assert response.text.startswith("You met Neha")
    assert response.confidence >= 0.65
    assert "optional planning" in response.explainability.reasoning_summary


def test_empty_archive_returns_helpful_200_response(monkeypatch):
    class NeverRetrieve:
        async def retrieve_memories(self, *_args, **_kwargs):
            raise AssertionError("empty archive must not trigger vector retrieval")

    monkeypatch.setattr(echo_module, "RetrievalService", NeverRetrieve)
    response = asyncio.run(conversation(
        EchoConversationRequest(question="What did my father do?"),
        {"sub": "owner-1"}, FakeConnection(memories=0, chunks=0, indexed=0),
    ))

    assert response.confidence == 0
    assert "Record a few conversations" in response.text


def test_only_final_provider_unavailability_returns_503(monkeypatch):
    class FakeRetrieval:
        async def retrieve_memories(self, *_args, **_kwargs):
            return [_retrieved_memory()]

    class FailingPlanner:
        async def plan(self, *_args, **_kwargs):
            raise ValueError("optional planner failure")

    class UnavailableGroq:
        async def complete(self, *_args, **_kwargs):
            raise GroqUnavailableError("provider timeout")

    monkeypatch.setattr(echo_module, "RetrievalService", FakeRetrieval)
    monkeypatch.setattr(echo_module, "CognitiveEngineService", FailingPlanner)
    monkeypatch.setattr(echo_module, "GroqService", UnavailableGroq)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(conversation(
            EchoConversationRequest(question="How did I meet my wife?"),
            {"sub": "owner-1"}, FakeConnection(),
        ))
    assert raised.value.status_code == 503
