"""Index durable memory chunks in Pinecone and keep their index state in Postgres."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg

from app.models.memory import MemoryFragment
from app.services.memory_chunking import MemoryChunk, build_memory_chunks

logger = logging.getLogger(__name__)


def vector_id_for(memory_id: str, chunk: MemoryChunk) -> str:
    """Return a deterministic vector id so retrying an index is an upsert."""
    return f"{memory_id}:{chunk.vector_id_suffix}"


def _memory_from_row(row: Any) -> MemoryFragment:
    """Normalise asyncpg JSONB codec variants before validating a memory."""
    payload = dict(row)
    for field, fallback in (("emotion_tags", []), ("topics", []), ("people_mentioned", []), ("semantic_metadata", {})):
        value = payload.get(field)
        if isinstance(value, str):
            try:
                payload[field] = json.loads(value)
            except json.JSONDecodeError:
                logger.warning("Memory %s has invalid %s JSON; using an empty fallback", payload.get("id"), field)
                payload[field] = fallback
        elif value is None:
            payload[field] = fallback
    return MemoryFragment.model_validate(payload)


async def _persist_chunks(
    conn: asyncpg.Connection,
    memory: MemoryFragment,
    owner_id: str,
    chunks: list[MemoryChunk],
) -> None:
    """Persist only derived retrieval data; never replace the source memory."""
    for chunk in chunks:
        await conn.execute(
            """
            INSERT INTO public.memory_chunks
              (user_id, memory_id, chunk_index, category, content, keywords, vector_id)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
            ON CONFLICT (memory_id, chunk_index) DO UPDATE SET
              category = EXCLUDED.category,
              content = EXCLUDED.content,
              keywords = EXCLUDED.keywords,
              vector_id = EXCLUDED.vector_id,
              updated_at = now()
            """,
            owner_id,
            memory.id,
            chunk.chunk_index,
            chunk.category,
            chunk.content,
            json.dumps(chunk.keywords),
            vector_id_for(str(memory.id), chunk),
        )


async def _mark_chunks_indexed(
    conn: asyncpg.Connection,
    memory_id: str,
    embedding_model: str,
    embedding_dimensions: int,
) -> None:
    await conn.execute(
        """
        UPDATE public.memory_chunks
        SET indexed_at = $2, embedding_model = $3, embedding_dimensions = $4, updated_at = now()
        WHERE memory_id = $1
        """,
        memory_id,
        datetime.now(timezone.utc),
        embedding_model,
        embedding_dimensions,
    )


def _vector_metadata(memory: MemoryFragment, owner_id: str, chunk: MemoryChunk) -> dict[str, Any]:
    metadata = memory.semantic_metadata or {}
    return {
        "memory_id": str(memory.id),
        "chunk_index": chunk.chunk_index,
        "subject_id": str(memory.subject_id),
        # Owner id and namespace are the canonical tenancy boundary.  A
        # subject record can have a different UUID in future multi-subject
        # accounts, whereas the memory owner is always unambiguous.
        "owner_id": str(owner_id),
        "user_id": str(owner_id),
        "session_id": str(memory.session_id),
        "consent_level": memory.consent_level.value,
        "emotion_tags": memory.emotion_tags,
        "topics": memory.topics,
        "people_mentioned": memory.people_mentioned,
        "confidence_score": memory.confidence_score,
        "time_period": memory.time_period or "",
        "category": chunk.category,
        "keywords": chunk.keywords,
        "content": chunk.content,
        "title": metadata.get("title", ""),
        "intent": metadata.get("intent", ""),
        "memory_type": metadata.get("memory_type", ""),
        "importance_score": metadata.get("importance_score", 0),
    }


async def _index_memory_async(
    memory_payload: dict,
    user_id: str,
    *,
    conn: asyncpg.Connection | None = None,
) -> list[MemoryChunk]:
    """Create story chunks, embed every one, and upsert all vectors.

    The caller may pass its request transaction connection.  If Postgres is
    temporarily unavailable, vector indexing can still proceed, but the
    missing ``indexed_at`` marker makes the gap visible and keyword fallback
    remains unavailable until a later reindex.
    """
    memory = MemoryFragment.model_validate(memory_payload)
    owner_id = str(user_id)
    chunks = build_memory_chunks(memory)
    if not chunks:
        raise ValueError("Cannot index a memory with no readable content")

    if conn is not None:
        await _persist_chunks(conn, memory, owner_id, chunks)

    from app.services.embedding_service import EmbeddingService
    from app.services.pinecone_service import PineconeService

    embedding_service = EmbeddingService()
    embedding_inputs = [chunk.content for chunk in chunks]
    embeddings = await embedding_service.embed_texts(embedding_inputs)
    if len(embeddings) != len(chunks):
        raise RuntimeError("Embedding provider returned an incomplete chunk batch")

    vectors = [
        {
            "id": vector_id_for(str(memory.id), chunk),
            "values": embedding,
            "metadata": _vector_metadata(memory, owner_id, chunk),
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    # Namespace by immutable owner, not by a presentation-layer subject id.
    PineconeService().upsert_vectors(owner_id, vectors)

    if conn is not None:
        await _mark_chunks_indexed(
            conn,
            str(memory.id),
            embedding_service.settings.gemini_embedding_model,
            len(embeddings[0]) if embeddings else 0,
        )
    logger.info("Indexed memory %s as %d story chunks for owner %s", memory.id, len(chunks), owner_id)
    return chunks


async def index_memory(
    memory_payload: dict,
    user_id: str,
    *,
    conn: asyncpg.Connection | None = None,
) -> list[MemoryChunk]:
    return await _index_memory_async(memory_payload, user_id, conn=conn)


async def reindex_owner_memories(conn: asyncpg.Connection, owner_id: str, *, limit: int = 100) -> int:
    """Repair missing chunk/vector records for an owner's existing memories.

    This makes the deployment self-healing: archives created before chunked
    indexing are re-embedded on their next retrieval instead of requiring an
    operator to export, delete, or manually re-upload an interview.
    """
    rows = await conn.fetch(
        """
        SELECT m.*
        FROM public.memories m
        WHERE m.user_id = $1
          AND (
            NOT EXISTS (SELECT 1 FROM public.memory_chunks c WHERE c.memory_id = m.id)
            OR EXISTS (
              SELECT 1 FROM public.memory_chunks c
              WHERE c.memory_id = m.id AND c.indexed_at IS NULL
            )
          )
        ORDER BY m.created_at ASC
        LIMIT $2
        """,
        owner_id,
        limit,
    )
    repaired = 0
    for row in rows:
        try:
            memory = _memory_from_row(row)
            await _index_memory_async(memory.model_dump(mode="json"), owner_id, conn=conn)
            repaired += 1
        except Exception:
            # Do not turn an otherwise valid question into a 500 merely
            # because one legacy memory needs provider attention.  Retrieval
            # below still searches its source text with Postgres keywords.
            logger.exception("Failed to repair retrieval index for memory %s", row["id"])
    if repaired:
        logger.info("Reindexed %d legacy memories for owner %s", repaired, owner_id)
    return repaired
