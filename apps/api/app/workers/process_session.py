import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.client import db_client
from app.db import repositories
from app.services.transcription_service import TranscriptionService
from app.services.memory_extractor import MemoryExtractorService
from app.models.memory import MemoryFragment

logger = get_task_logger(__name__)


def _reconcile_extracted_memories(extracted_memories):
    """Merge exact draft-like duplicates without ever discarding source evidence.

    The extractor can emit the same passage in overlapping transcript windows.
    This is a deterministic pre-persistence reconciliation step; it does not
    choose between conflicting memories or alter any already stored record.
    """
    reconciled = {}
    for memory in extracted_memories:
        key = " ".join(memory.content.lower().split())
        existing = reconciled.get(key)
        if not existing:
            reconciled[key] = memory
            continue
        existing.emotion_tags = sorted(set(existing.emotion_tags) | set(memory.emotion_tags))
        existing.topics = sorted(set(existing.topics) | set(memory.topics))
        existing.people_mentioned = sorted(set(existing.people_mentioned) | set(memory.people_mentioned))
        existing.confidence_score = max(existing.confidence_score, memory.confidence_score)
    return list(reconciled.values())


async def _process_session_async(session_id: str):
    logger.info(f"Starting memory extraction pipeline for session {session_id}")
    
    # 1. Fetch session
    # We must ensure the db_client pool is initialized if running outside FastAPI lifespan
    if not db_client.pool:
        await db_client.connect()
        
    async with db_client.pool.acquire() as conn:
        session = await repositories.get_session(conn, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return
            
        # Check idempotency - do we already have memories?
        count_query = "SELECT COUNT(*) FROM memories WHERE session_id = $1"
        existing_count = await conn.fetchval(count_query, session_id)
        if existing_count > 0:
            logger.info(f"Session {session_id} already has {existing_count} memories. Skipping extraction.")
            return

        audio_url = session.audio_url
        subject_id = session.subject_id
        user_id = await conn.fetchval("SELECT user_id FROM sessions WHERE id = $1", session_id)

    if not audio_url:
        logger.warning(f"No audio URL for session {session_id}. Cannot extract memories.")
        return

    # 2. Download and Transcribe
    transcription_service = TranscriptionService()
    try:
        audio_file_path = await transcription_service.download_audio(audio_url)
        logger.info(f"Audio downloaded to {audio_file_path}")
        
        chunks = await transcription_service.transcribe_and_segment(audio_file_path)
        logger.info(f"Transcribed into {len(chunks)} semantic chunks.")
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise
        
    # 3. Extract structured memories
    memory_extractor = MemoryExtractorService()
    try:
        extracted_memories = await memory_extractor.extract_memories(chunks)
        extracted_memories = _reconcile_extracted_memories(extracted_memories)
        logger.info(f"Extracted {len(extracted_memories)} structured memories.")
    except Exception as e:
        logger.error(f"Memory extraction failed: {str(e)}")
        raise
        
    # 4. Save to Database
    async with db_client.pool.acquire() as conn:
        now = datetime.now(timezone.utc)
        memories_to_insert = []
        for em in extracted_memories:
            mem = MemoryFragment(
                id=str(uuid4()),
                session_id=session_id,
                subject_id=subject_id,
                content=em.content,
                emotion_tags=em.emotion_tags,
                topics=em.topics,
                people_mentioned=em.people_mentioned,
                time_period=em.time_period,
                confidence_score=em.confidence_score,
                created_at=now,
                search_document=em.search_document,
                semantic_metadata=em.semantic_metadata,
            )
            memories_to_insert.append(mem)
            await repositories.create_memory(conn, mem, user_id)
            
    logger.info(f"Successfully processed session {session_id} into PostgreSQL")

    # 5. Embed and Upsert to Pinecone
    try:
        from app.services.embedding_service import EmbeddingService
        from app.services.pinecone_service import PineconeService
        
        embedding_service = EmbeddingService()
        pinecone_service = PineconeService()
        
        serialized_texts = [embedding_service.serialize_memory(m) for m in memories_to_insert]
        embeddings = await embedding_service.embed_texts(serialized_texts)
        
        vectors = []
        for m, emb in zip(memories_to_insert, embeddings):
            vectors.append({
                "id": str(m.id),
                "values": emb,
                "metadata": {
                    "memory_id": str(m.id),
                    "subject_id": str(m.subject_id),
                    "user_id": str(user_id),
                    "session_id": str(m.session_id),
                    "consent_level": m.consent_level.value,
                    "emotion_tags": m.emotion_tags,
                    "topics": m.topics,
                    "confidence_score": m.confidence_score,
                    "time_period": m.time_period or "",
                    "content": m.content,
                    "title": m.semantic_metadata.get("title", ""),
                    "keywords": m.semantic_metadata.get("keywords", []),
                    "intent": m.semantic_metadata.get("intent", ""),
                    "memory_type": m.semantic_metadata.get("memory_type", ""),
                    "importance_score": m.semantic_metadata.get("importance_score", 0),
                }
            })
            
        if vectors:
            pinecone_service.upsert_vectors(str(subject_id), vectors)
            logger.info(f"Successfully upserted {len(vectors)} vectors to Pinecone.")
            
    except Exception as e:
        logger.error(f"Failed to embed and upsert to Pinecone: {e}")
        raise
        
    # 6. Trigger Persona Retraining Check
    try:
        from app.workers.task_runner import run_task
        run_task("retrain_persona", str(subject_id))
        logger.info(f"Triggered retrain_persona check for subject {subject_id}")
    except Exception as e:
        logger.error(f"Failed to trigger retraining: {e}")

@celery_app.task(bind=True, max_retries=3, name="process_session")
def process_session(self, session_id: str):
    """Celery entry point for the durable post-session processing pipeline."""
    try:
        # Create a new event loop for this thread if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(_process_session_async(session_id))
    except Exception as exc:
        logger.error(f"Error processing session {session_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


# Keep imports from older deployments working while the production dispatcher
# uses the clear `process_session.delay(session_id)` API.
process_session_task = process_session
