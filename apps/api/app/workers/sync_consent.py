"""Synchronise a durable memory-consent change to Pinecone metadata."""

import asyncio
from celery.utils.log import get_task_logger

from app.db import repositories
from app.db.client import db_client
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


async def _sync_memory_consent_async(memory_id: str, user_id: str) -> None:
    """Read the final owned row before updating its matching Pinecone vector.

    The task deliberately receives no consent level or namespace from the
    browser. A delayed task therefore cannot overwrite a newer change, nor can
    it ever select a vector outside the memory owner's namespace.
    """
    if not db_client.pool:
        await db_client.connect()
    if not db_client.pool:
        raise RuntimeError("Database is unavailable for consent synchronization")

    async with db_client.pool.acquire() as conn:
        memory = await repositories.get_memory(conn, memory_id, user_id)
    if not memory:
        logger.warning("Consent sync skipped: memory %s is unavailable to user %s", memory_id, user_id)
        return

    from app.services.pinecone_service import PineconeService
    PineconeService().update_metadata(
        str(memory.subject_id),
        str(memory.id),
        {"consent_level": memory.consent_level.value},
    )
    logger.info("Pinecone consent metadata synchronized for memory %s", memory_id)


@celery_app.task(bind=True, max_retries=2, name="sync_memory_consent")
def sync_memory_consent(self, memory_id: str, user_id: str):
    """Retry short-lived provider failures without delaying the PATCH response."""
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(_sync_memory_consent_async(memory_id, user_id))
    except Exception as error:
        logger.exception("Pinecone consent sync failed for memory %s", memory_id)
        raise self.retry(exc=error, countdown=2)
