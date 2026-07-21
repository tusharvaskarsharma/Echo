"""Conversation endpoint failure classification and planner fallback coverage."""

import asyncio

import pytest
from fastapi import HTTPException

import app.routers.emmy_conversation as emmy_module
from app.routers.emmy_conversation import EmmyConversationRequest, conversation
from app.services.groq_service import GroqUnavailableError


class FakeConnection:
    def __init__(self, *, memories=1, chunks=1, indexed=1, identity=None):
        self.memories, self.chunks, self.indexed = memories, chunks, indexed
        self.identity = identity

    async def fetchrow(self, query, *_args):
        if "FROM subjects" in query:
            return {"id": "owner-1", "user_id": "owner-1", "full_name": "Test"}
        if "FROM public.identity_profiles" in query:
            return self.identity
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

    monkeypatch.setattr(emmy_module, "RetrievalService", FakeRetrieval)
    monkeypatch.setattr(emmy_module, "CognitiveEngineService", FailingPlanner)
    monkeypatch.setattr(emmy_module, "GroqService", FakeGroq)

    response = asyncio.run(conversation(
        EmmyConversationRequest(question="How did I meet my wife?"),
        {"sub": "owner-1"}, FakeConnection(),
    ))

    assert response.text.startswith("You met Neha")
    assert response.confidence >= 0.65
    assert "optional planning" in response.explainability.reasoning_summary


def test_empty_archive_returns_helpful_200_response(monkeypatch):
    class NeverRetrieve:
        async def retrieve_memories(self, *_args, **_kwargs):
            raise AssertionError("empty archive must not trigger vector retrieval")

    monkeypatch.setattr(emmy_module, "RetrievalService", NeverRetrieve)
    response = asyncio.run(conversation(
        EmmyConversationRequest(question="What did my father do?"),
        {"sub": "owner-1"}, FakeConnection(memories=0, chunks=0, indexed=0),
    ))

    assert response.confidence == 0
    assert "Record a few conversations" in response.text


def test_identity_question_bypasses_semantic_retrieval(monkeypatch):
    class NeverRetrieve:
        async def retrieve_memories(self, *_args, **_kwargs):
            raise AssertionError("identity questions must not invoke semantic retrieval")

    monkeypatch.setattr(emmy_module, "RetrievalService", NeverRetrieve)
    response = asyncio.run(conversation(
        EmmyConversationRequest(question="What is your occupation?"),
        {"sub": "owner-1"}, FakeConnection(identity={"user_id": "owner-1", "occupation": "School teacher", "privacy_settings": {"shared_fields": []}}),
    ))

    assert response.text == "Their occupation is School teacher."
    assert response.confidence == 0.98


def test_chunks_can_answer_through_keyword_fallback_before_vector_indexing(monkeypatch):
    class KeywordRetrieval:
        async def retrieve_memories(self, *_args, **_kwargs):
            return [_retrieved_memory()]

    class FailingPlanner:
        async def plan(self, *_args, **_kwargs):
            raise ValueError("planner is optional")

    class FakeGroq:
        async def complete(self, *_args, **_kwargs):
            return "You met Neha through a mutual friend."

    monkeypatch.setattr(emmy_module, "RetrievalService", KeywordRetrieval)
    monkeypatch.setattr(emmy_module, "CognitiveEngineService", FailingPlanner)
    monkeypatch.setattr(emmy_module, "GroqService", FakeGroq)
    response = asyncio.run(conversation(
        EmmyConversationRequest(question="How did I meet my wife?"),
        {"sub": "owner-1"}, FakeConnection(memories=1, chunks=1, indexed=0),
    ))

    assert response.text.startswith("You met Neha")


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

    monkeypatch.setattr(emmy_module, "RetrievalService", FakeRetrieval)
    monkeypatch.setattr(emmy_module, "CognitiveEngineService", FailingPlanner)
    monkeypatch.setattr(emmy_module, "GroqService", UnavailableGroq)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(conversation(
            EmmyConversationRequest(question="How did I meet my wife?"),
            {"sub": "owner-1"}, FakeConnection(),
        ))
    assert raised.value.status_code == 503
