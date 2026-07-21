"""Synchronise a durable memory-consent change to Pinecone metadata."""

import logging

from app.db import repositories
from app.db.client import db_client

logger = logging.getLogger(__name__)


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


async def sync_memory_consent(memory_id: str, user_id: str) -> None:
    await _sync_memory_consent_async(memory_id, user_id)
