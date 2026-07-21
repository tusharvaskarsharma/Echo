"""Consent-aware hybrid retrieval over Pinecone vectors and durable chunks."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import asyncpg

from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)

WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "for", "from", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "that", "the", "their", "they", "to", "was", "what", "when", "who", "with", "you", "your",
})


def _question_terms(question: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for term in WORD.findall(question.lower()):
        if term in STOP_WORDS or len(term) < 2 or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def _normalise_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _keyword_score(question_terms: list[str], candidate: dict[str, Any]) -> float:
    if not question_terms:
        return 0.0
    searchable = " ".join([
        str(candidate.get("content") or ""),
        str(candidate.get("category") or ""),
        " ".join(_normalise_list(candidate.get("keywords"))),
        " ".join(_normalise_list(candidate.get("topics"))),
        " ".join(_normalise_list(candidate.get("people_mentioned"))),
    ]).lower()
    matches = sum(1 for term in question_terms if re.search(rf"\b{re.escape(term)}\b", searchable))
    return matches / len(question_terms)


def _candidate_key(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('memory_id') or candidate.get('id')}:{candidate.get('chunk_index', 0)}"


class RetrievalService:
    """Retrieve several independently useful chunks, never one whole interview."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_service: PineconeService | None = None

    async def _ensure_legacy_index(self, conn: asyncpg.Connection | None, owner_id: str) -> None:
        if conn is None:
            return
        try:
            from app.workers.index_memory import reindex_owner_memories

            await reindex_owner_memories(conn, owner_id)
        except Exception:
            # Retrieval remains available through the Postgres keyword path.
            logger.exception("Legacy reindex check failed for owner %s", owner_id)

    async def _keyword_candidates(
        self,
        conn: asyncpg.Connection | None,
        question: str,
        owner_id: str,
        allowed_consent_levels: list[str],
        question_terms: list[str],
    ) -> list[dict[str, Any]]:
        if conn is None or not question_terms:
            return []
        patterns = [f"%{term}%" for term in question_terms]
        try:
            rows = await conn.fetch(
                """
                WITH query AS (
                  SELECT websearch_to_tsquery('english', $3) AS terms
                )
                SELECT
                  c.vector_id AS embedding_id, c.memory_id, c.chunk_index, c.category, c.content, c.keywords,
                  m.session_id, m.subject_id, m.consent_level, m.emotion_tags, m.topics,
                  m.people_mentioned, m.time_period, m.confidence_score,
                  ts_rank_cd(to_tsvector('english', c.content), query.terms) AS database_keyword_rank
                FROM public.memory_chunks c
                JOIN public.memories m ON m.id = c.memory_id
                CROSS JOIN query
                WHERE c.user_id = $1
                  AND m.consent_level = ANY($2::text[])
                  AND (
                    to_tsvector('english', c.content) @@ query.terms
                    OR lower(c.content) LIKE ANY($4::text[])
                    OR EXISTS (
                      SELECT 1
                      FROM jsonb_array_elements_text(c.keywords) AS keyword(value)
                      WHERE lower(keyword.value) = ANY($5::text[])
                    )
                  )
                ORDER BY database_keyword_rank DESC, c.updated_at DESC
                LIMIT 24
                """,
                owner_id,
                allowed_consent_levels,
                question,
                patterns,
                question_terms,
            )
        except asyncpg.PostgresError:
            logger.exception("Keyword retrieval query failed for owner %s", owner_id)
            return []

        return [dict(row) for row in rows]

    async def retrieve_memories(
        self,
        question: str,
        owner_id: str,
        allowed_consent_levels: List[str],
        *,
        conn: asyncpg.Connection | None = None,
        min_score: float = 0.35,
        top_k: int = 6,
    ) -> List[Dict[str, Any]]:
        """Use semantic candidates, keyword candidates, metadata, then rerank.

        ``owner_id`` is both Pinecone namespace and hard tenancy filter.  The
        caller has already proved whether the current user may use the
        requested consent levels.
        """
        question = question.strip()
        terms = _question_terms(question)
        logger.info("Retrieval question=%r owner=%s terms=%s", question, owner_id, terms)
        await self._ensure_legacy_index(conn, owner_id)

        candidates: dict[str, dict[str, Any]] = {}
        keyword_candidates = await self._keyword_candidates(conn, question, owner_id, allowed_consent_levels, terms)
        for candidate in keyword_candidates:
            candidate["semantic_score"] = 0.0
            candidates[_candidate_key(candidate)] = candidate

        try:
            embeddings = await self.embedding_service.embed_texts([question])
            if not embeddings:
                raise RuntimeError("Embedding provider returned no question vector")
            if self.pinecone_service is None:
                self.pinecone_service = PineconeService()
            matches = self.pinecone_service.query(
                namespace=owner_id,
                vector=embeddings[0],
                # Query broadly, then cap after lexical/semantic reranking.
                top_k=24,
                filter={
                    "owner_id": {"$eq": owner_id},
                    "consent_level": {"$in": allowed_consent_levels},
                },
            )
        except Exception:
            # A Pinecone or embedding outage must not conceal exact evidence
            # that Postgres can retrieve by keyword.
            logger.exception("Semantic retrieval failed for owner %s; using keyword candidates", owner_id)
            matches = []

        for match in matches:
            metadata = dict(match.get("metadata") or {})
            if not metadata.get("content"):
                continue
            metadata["embedding_id"] = str(match.get("id") or metadata.get("embedding_id") or "")
            metadata["semantic_score"] = float(match.get("score") or 0.0)
            key = _candidate_key(metadata)
            existing = candidates.get(key)
            if existing:
                existing.update({key: value for key, value in metadata.items() if value not in (None, "", [], {})})
                existing["semantic_score"] = max(float(existing.get("semantic_score") or 0.0), metadata["semantic_score"])
            else:
                candidates[key] = metadata

        ranked: list[dict[str, Any]] = []
        for candidate in candidates.values():
            semantic = float(candidate.get("semantic_score") or 0.0)
            keyword = _keyword_score(terms, candidate)
            # Pinecone scores below the old 0.52/0.72 hard cut are still
            # useful when a question shares precise family names or facts.
            if semantic < min_score and keyword == 0:
                continue
            candidate["keyword_score"] = round(keyword, 4)
            candidate["retrieval_score"] = round((semantic * 0.68) + (keyword * 0.32), 4)
            candidate["id"] = str(candidate.get("memory_id") or candidate.get("id") or "")
            ranked.append(candidate)

        ranked.sort(key=lambda item: (float(item["retrieval_score"]), float(item.get("semantic_score") or 0.0)), reverse=True)

        # Avoid filling the prompt with many pieces of the same paragraph while
        # still allowing a multi-part story to bring a second supporting chunk.
        selected: list[dict[str, Any]] = []
        per_memory: dict[str, int] = {}
        for candidate in ranked:
            memory_id = str(candidate.get("memory_id") or candidate.get("id"))
            if per_memory.get(memory_id, 0) >= 2:
                continue
            selected.append(candidate)
            per_memory[memory_id] = per_memory.get(memory_id, 0) + 1
            if len(selected) == top_k:
                break

        logger.info(
            "Retrieval selected=%s",
            [
                {
                    "memory_id": item.get("memory_id"),
                    "embedding_id": item.get("embedding_id"),
                    "semantic_score": item.get("semantic_score"),
                    "keyword_score": item.get("keyword_score"),
                    "retrieval_score": item.get("retrieval_score"),
                    "category": item.get("category"),
                }
                for item in selected
            ],
        )
        logger.debug("Retrieved evidence chunks=%r", [item.get("content") for item in selected])
        return selected
