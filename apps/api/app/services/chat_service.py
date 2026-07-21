"""Consent-aware family conversation streaming service."""

import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.models.emmy import Citation
from app.services.groq_service import GroqService
from app.services.persona_service import PersonaService
from app.services.retrieval_service import RetrievalService
from app.services.identity_service import (
    IdentityIntent, IdentityService, answer_identity_question, build_identity_context, classify_question,
)

logger = logging.getLogger(__name__)
NO_MEMORY_RESPONSE = "I don't have a memory of that — I wish I did."


class ChatService:
    def __init__(self, conn):
        self.conn = conn
        self.groq = GroqService()
        self.retrieval_service = RetrievalService()
        self.persona_service = PersonaService()

    @staticmethod
    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def converse_stream(self, emmy_id: str, user_id: str, access_level: str, text: str | None = None, audio_path: str | None = None):
        if audio_path:
            segments = await self.groq.transcribe(audio_path)
            text = " ".join(segment.get("text", "") for segment in segments).strip()
        if not text:
            raise ValueError("Either text or audio must be provided.")

        profile = await self.conn.fetchrow("SELECT subject_id FROM emmy_profiles WHERE id = $1", emmy_id)
        if not profile:
            raise ValueError("Emmy profile not found.")
        subject_id = str(profile["subject_id"])
        owner_id = await self.conn.fetchval("SELECT user_id FROM subjects WHERE id = $1", subject_id)
        if not owner_id:
            raise ValueError("Emmy profile has no owning user.")
        allowed_consent = {
            "owner": ["private", "family", "legacy"],
            "family": ["family", "legacy"],
            "legacy": ["legacy"],
        }.get(access_level, ["legacy"])
        subject = await self.conn.fetchrow("SELECT full_name FROM subjects WHERE id = $1", subject_id)
        subject_name = subject["full_name"] if subject else "Your loved one"
        identity = await IdentityService().load_for_access(
            self.conn, str(owner_id), is_owner=access_level == "owner", fallback_name=subject_name,
        )
        intent = classify_question(text)
        direct_answer = answer_identity_question(text, identity) if intent == IdentityIntent.IDENTITY else None
        if direct_answer:
            async def identity_response():
                yield self._sse({"type": "text", "text": direct_answer})
                yield self._sse({"type": "sources", "sources": []})
                yield self._sse({"type": "done"})
            return identity_response()
        if intent == IdentityIntent.IDENTITY:
            async def unknown_identity_response():
                yield self._sse({"type": "text", "text": "I don't have that detail in the Life Profile yet. You can add it from Life Profile."})
                yield self._sse({"type": "sources", "sources": []})
                yield self._sse({"type": "done"})
            return unknown_identity_response()
        memories = await self.retrieval_service.retrieve_memories(
            text, str(owner_id), allowed_consent, conn=self.conn,
            min_score=0.35 if access_level == "owner" else 0.45, top_k=6,
        )

        if not memories:
            async def fallback():
                yield self._sse({"type": "text", "text": NO_MEMORY_RESPONSE})
                yield self._sse({"type": "sources", "sources": []})
                yield self._sse({"type": "done"})
            return fallback()

        prompt = self.persona_service.build_prompt(
            subject_name=subject_name,
            persona_details={"style": "Warm, loving, and slightly nostalgic"},
            memories=memories,
            identity_context=build_identity_context(identity),
        )
        sources, memory_ids = await self._sources(memories)

        async def stream():
            started = time.monotonic()
            full_response = ""
            try:
                async for fragment in self.groq.stream_chat([
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ]):
                    full_response += fragment
                    yield self._sse({"type": "text", "text": fragment})
                yield self._sse({"type": "sources", "sources": [source.model_dump() for source in sources]})
                yield self._sse({"type": "done"})
                await self.conn.execute(
                    """INSERT INTO conversation_history
                    (id, emmy_profile_id, user_id, question, response, memory_ids, latency_ms, token_usage, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)""",
                    str(uuid4()), emmy_id, user_id, text, full_response, json.dumps(memory_ids),
                    int((time.monotonic() - started) * 1000), len(full_response) // 4, datetime.now(timezone.utc),
                )
            except Exception:
                logger.exception("Family conversation stream failed")
                yield self._sse({"type": "error", "message": "Emmy could not complete that grounded response. Please try again."})
                yield self._sse({"type": "done"})

        return stream()

    async def _sources(self, memories: list[dict]) -> tuple[list[Citation], list[str]]:
        session_ids = [str(memory["session_id"]) for memory in memories if memory.get("session_id")]
        timestamps: dict[str, str] = {}
        if session_ids:
            rows = await self.conn.fetch("SELECT id, started_at FROM sessions WHERE id = ANY($1::uuid[])", session_ids)
            timestamps = {str(row["id"]): row["started_at"].isoformat() if row["started_at"] else "Unknown date" for row in rows}
        sources, memory_ids = [], []
        for memory in memories:
            memory_id = memory.get("memory_id")
            if not memory_id:
                continue
            memory_ids.append(str(memory_id))
            content = memory.get("content", "")
            sources.append(Citation(
                memory_id=str(memory_id),
                session_id=str(memory.get("session_id", "")),
                timestamp=timestamps.get(str(memory.get("session_id")), memory.get("time_period") or "Unknown date"),
                excerpt=content[:180] + ("…" if len(content) > 180 else ""),
            ))
        return sources, memory_ids
