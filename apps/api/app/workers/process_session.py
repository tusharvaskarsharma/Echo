"""Synchronous structured-memory processing with complete transcript preservation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.db import repositories
from app.db.client import db_client
from app.models.memory import ConsentLevel, MemoryFragment
from app.services.memory_chunking import StoryUnit, build_story_units
from app.services.memory_extractor import ExtractedMemory, MemoryExtractorService
from app.services.transcription_service import TranscriptionService
from app.workers.index_memory import index_memories

logger = logging.getLogger(__name__)
INGESTION_FORMAT = "structured-story-v2"


def _transcript_from_segments(segments: list[dict]) -> str:
    return "\n".join(str(segment.get("text") or "").strip() for segment in segments if segment.get("text")).strip()


def _fallback_search_document(unit: StoryUnit) -> str:
    return (
        f"Title: {unit.title}. Category: {unit.category}. Summary: {unit.summary}. "
        f"Keywords: {', '.join(unit.keywords)}. Source evidence: {unit.content}"
    )


def _memory_from_story(
    unit: StoryUnit,
    enriched: ExtractedMemory | None,
    *,
    session_id: str,
    subject_id: str,
) -> MemoryFragment:
    """Create a durable structured memory while retaining its original story."""
    semantic = dict(enriched.semantic_metadata) if enriched else {}
    extracted_category = str(semantic.get("category") or "")
    category = unit.category if extracted_category in {"", "Stories"} and unit.category != "Stories" else (extracted_category or unit.category)
    tags = list(dict.fromkeys([
        category.lower(), *unit.keywords,
        *[str(value) for value in semantic.get("keywords", []) if value],
    ]))[:32]
    metadata = {
        "source": "session_transcript",
        "ingestion_format": INGESTION_FORMAT,
        "title": str(semantic.get("title") or unit.title),
        "summary": str(semantic.get("summary") or unit.summary),
        "category": category,
        "important_facts": semantic.get("important_facts", []),
        "user_preferences": semantic.get("user_preferences", []),
        "people": semantic.get("people", []),
        "places": semantic.get("places", []),
        "objects": semantic.get("objects", []),
        "time_reference": semantic.get("time_reference"),
        "keywords": tags,
        "tags": tags,
        "importance_score": float(semantic.get("importance_score") or unit.importance_score),
        "importance_level": semantic.get("importance_level") or (
            "critical" if unit.importance_score >= 0.95 else "high" if unit.importance_score >= 0.8 else "medium"
        ),
        "related_memory_ids": [],
    }
    topics = semantic.get("topics") if isinstance(semantic.get("topics"), list) else []
    people = semantic.get("people") if isinstance(semantic.get("people"), list) else []
    return MemoryFragment(
        id=str(uuid4()), session_id=session_id, subject_id=subject_id,
        content=unit.content,
        emotion_tags=(enriched.emotion_tags if enriched else ["reflective"]),
        topics=[str(topic) for topic in topics] or [category.lower()],
        people_mentioned=[str(person) for person in people],
        consent_level=ConsentLevel.PRIVATE,
        confidence_score=(enriched.confidence_score if enriched else 0.8),
        created_at=datetime.now(timezone.utc),
        search_document=(enriched.search_document if enriched else _fallback_search_document(unit)),
        semantic_metadata=metadata,
    )


async def _link_related_memories(conn, memories: list[MemoryFragment]) -> list[MemoryFragment]:
    """Link sibling stories when they share a category, person, or topic."""
    linked: list[MemoryFragment] = []
    for memory in memories:
        metadata = dict(memory.semantic_metadata or {})
        category = str(metadata.get("category") or "Stories")
        people = {str(person).lower() for person in memory.people_mentioned}
        topics = {str(topic).lower() for topic in memory.topics}
        related_ids: list[str] = []
        for other in memories:
            if other.id == memory.id:
                continue
            other_metadata = other.semantic_metadata or {}
            same_category = category == str(other_metadata.get("category") or "Stories")
            shares_person = bool(people & {str(person).lower() for person in other.people_mentioned})
            shares_topic = bool(topics & {str(topic).lower() for topic in other.topics})
            if same_category or shares_person or shares_topic:
                related_ids.append(str(other.id))
        metadata["related_memory_ids"] = related_ids[:8]
        await conn.execute(
            "UPDATE public.memories SET semantic_metadata = $1::jsonb WHERE id = $2",
            json.dumps(metadata), memory.id,
        )
        linked.append(memory.model_copy(update={"semantic_metadata": metadata}))
    return linked


async def _process_session_async(session_id: str) -> None:
    """Preserve a transcript, then create one searchable memory per story."""
    logger.info("Starting synchronous structured memory processing session=%s", session_id)
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
            logger.info("Session %s already has %s structured source memories", session_id, existing_count)
            return
        owner_id = await conn.fetchval("SELECT user_id FROM public.sessions WHERE id = $1", session_id)
        if not owner_id:
            raise RuntimeError("Session has no owning user")
        transcript = (session.transcript or "").strip()
        audio_url = session.audio_url

    segments: list[dict] = []
    if not transcript:
        if not audio_url:
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
                transcript, json.dumps(segments), session_id,
            )

    units = build_story_units(transcript, ["interview"])
    if not units:
        logger.info("Session %s has no complete story units", session_id)
        return
    logger.info("Split session %s into %d complete story units", session_id, len(units))

    enriched_by_index: dict[int, ExtractedMemory] = {}
    try:
        enriched_by_index = await MemoryExtractorService().extract_structured_memories([unit.content for unit in units])
        logger.info("Enriched %d/%d structured memories for session %s", len(enriched_by_index), len(units), session_id)
    except Exception:
        # The deterministic structured units still retain all evidence and are
        # searchable if an enrichment provider is unavailable.
        logger.exception("Semantic enrichment failed for session %s; using deterministic metadata", session_id)

    memories = [
        _memory_from_story(
            unit, enriched_by_index.get(index), session_id=session_id, subject_id=str(session.subject_id),
        )
        for index, unit in enumerate(units)
    ]

    async with db_client.pool.acquire() as conn:
        async with conn.transaction():
            saved_memories = [await repositories.create_memory(conn, memory, owner_id) for memory in memories]
            saved_memories = await _link_related_memories(conn, saved_memories)
        try:
            await index_memories(
                [memory.model_dump(mode="json") for memory in saved_memories], str(owner_id), conn=conn,
            )
        except Exception:
            # Database source records are committed first. Retrieval will
            # reindex safely later, while Postgres keyword search remains live.
            logger.exception("Structured memories stored but Pinecone indexing failed session=%s", session_id)

    try:
        from app.workers.retrain_persona import retrain_persona

        await retrain_persona(str(session.subject_id))
    except Exception:
        logger.exception("Persona retraining check failed for session %s", session_id)

    logger.info("Processed session %s into %d structured memories", session_id, len(memories))


async def process_session(session_id: str) -> None:
    await _process_session_async(session_id)
