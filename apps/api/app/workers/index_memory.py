"""Index a single already-persisted memory without requiring direct Postgres access."""

import logging

from app.models.memory import MemoryFragment

logger = logging.getLogger(__name__)


async def _index_memory_async(memory_payload: dict, user_id: str) -> None:
    memory = MemoryFragment.model_validate(memory_payload)
    # This job is only enqueued by authenticated server routes. Assert the
    # fallback invariant anyway: a user can index only their own namespace.
    if str(memory.subject_id) != str(user_id):
        raise ValueError("Memory subject does not match the indexing owner")

    from app.services.embedding_service import EmbeddingService
    from app.services.pinecone_service import PineconeService

    embedding_service = EmbeddingService()
    embeddings = await embedding_service.embed_texts([embedding_service.serialize_memory(memory)])
    if not embeddings:
        raise RuntimeError("No embedding returned for memory")
    PineconeService().upsert_vectors(str(memory.subject_id), [{
        "id": str(memory.id),
        "values": embeddings[0],
        "metadata": {
            "memory_id": str(memory.id),
            "subject_id": str(memory.subject_id),
            "user_id": str(user_id),
            "session_id": str(memory.session_id),
            "consent_level": memory.consent_level.value,
            "emotion_tags": memory.emotion_tags,
            "topics": memory.topics,
            "confidence_score": memory.confidence_score,
                    "time_period": memory.time_period or "",
                    "content": memory.content,
                    "title": memory.semantic_metadata.get("title", ""),
                    "keywords": memory.semantic_metadata.get("keywords", []),
                    "intent": memory.semantic_metadata.get("intent", ""),
                    "memory_type": memory.semantic_metadata.get("memory_type", ""),
                    "importance_score": memory.semantic_metadata.get("importance_score", 0),
        },
    }])
    logger.info("Indexed memory %s in Pinecone namespace %s", memory.id, memory.subject_id)


async def index_memory(memory_payload: dict, user_id: str) -> None:
    await _index_memory_async(memory_payload, user_id)
