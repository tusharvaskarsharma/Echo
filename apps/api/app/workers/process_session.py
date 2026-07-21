"""Synchronous interview processing with complete transcript preservation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.db import repositories
from app.db.client import db_client
from app.models.memory import ConsentLevel, MemoryFragment
from app.services.memory_extractor import MemoryExtractorService
from app.services.transcription_service import TranscriptionService
from app.workers.index_memory import index_memory

logger = logging.getLogger(__name__)


def _transcript_from_segments(segments: list[dict]) -> str:
    return "\n".join(str(segment.get("text") or "").strip() for segment in segments if segment.get("text")).strip()


async def _process_session_async(session_id: str) -> None:
    """Persist full evidence first, then enrich and index it.

    A failed semantic summary or vector write may not delete or hide an
    interview.  The stored transcript remains available for a later repair.
    """
    logger.info("Starting synchronous memory processing for session %s", session_id)
    if not db_client.pool:
        await db_client.connect()
    if not db_client.pool:
        raise RuntimeError("Database is unavailable for session processing")

    async with db_client.pool.acquire() as conn:
        session = await repositories.get_session(conn, session_id)
        if not session:
            logger.error("Session %s not found", session_id)
            return
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM public.memories WHERE session_id = $1", session_id)
        if existing_count:
            logger.info("Session %s already has %s source memories; keeping its existing evidence", session_id, existing_count)
            return
        owner_id = await conn.fetchval("SELECT user_id FROM public.sessions WHERE id = $1", session_id)
        if not owner_id:
            raise RuntimeError("Session has no owning user")
        transcript = (session.transcript or "").strip()
        audio_url = session.audio_url

    segments: list[dict] = []
    if not transcript:
        if not audio_url:
            # A completed but empty session is not an extraction error.  This
            # commonly happens when a caller disconnects before speaking.
            logger.info("Session %s has no transcript or audio; no memory created", session_id)
            return
        try:
            audio_file_path = await TranscriptionService().download_audio(audio_url)
            segments = await TranscriptionService().transcribe_and_segment(audio_file_path)
            transcript = _transcript_from_segments(segments)
        except Exception:
            logger.exception("Audio transcription failed for session %s", session_id)
            raise
        if not transcript:
            logger.info("Session %s transcription contained no speech", session_id)
            return
        async with db_client.pool.acquire() as conn:
            await conn.execute(
                """UPDATE public.sessions
                   SET transcript = $1, transcript_segments = $2::jsonb
                   WHERE id = $3""",
                transcript,
                json.dumps(segments),
                session_id,
            )

    # A structured summary is useful metadata, but the exact transcript—not
    # a lossy summary—is the canonical content chunked and embedded below.
    metadata: dict = {"source": "session_transcript", "chunking": "question_answer_and_paragraph_v1"}
    topics = ["interview"]
    people: list[str] = []
    emotion_tags = ["reflective"]
    confidence = 0.85
    try:
        extraction_input = segments or [{"start": 0, "end": 0, "text": transcript}]
        extracted = await MemoryExtractorService().extract_memories(extraction_input)
        if extracted:
            summary = extracted[0]
            metadata.update(summary.semantic_metadata)
            topics = summary.topics or topics
            people = summary.people_mentioned
            emotion_tags = summary.emotion_tags or emotion_tags
            confidence = summary.confidence_score
    except Exception:
        logger.exception("Semantic enrichment failed for session %s; retaining raw transcript", session_id)

    memory = MemoryFragment(
        id=str(uuid4()),
        session_id=session_id,
        subject_id=session.subject_id,
        content=transcript,
        emotion_tags=emotion_tags,
        topics=topics,
        people_mentioned=people,
        consent_level=ConsentLevel.PRIVATE,
        confidence_score=confidence,
        created_at=datetime.now(timezone.utc),
        # Preserve raw evidence so no generator is asked to rely on a lossy
        # paraphrase.  Indexing itself embeds its story chunks directly.
        search_document=transcript,
        semantic_metadata=metadata,
    )

    async with db_client.pool.acquire() as conn:
        saved = await repositories.create_memory(conn, memory, owner_id)
        try:
            await index_memory(saved.model_dump(mode="json"), str(owner_id), conn=conn)
        except Exception:
            # The source transcript is committed.  Retrieval will repair a
            # missing vector synchronously on a later question and keyword
            # retrieval has the persisted chunks if embedding alone failed.
            logger.exception("Memory %s stored but Pinecone indexing failed", saved.id)

    try:
        from app.workers.retrain_persona import retrain_persona

        await retrain_persona(str(session.subject_id))
    except Exception:
        logger.exception("Persona retraining check failed for session %s", session_id)

    logger.info("Processed session %s into durable transcript memory %s", session_id, memory.id)


async def process_session(session_id: str) -> None:
    await _process_session_async(session_id)
