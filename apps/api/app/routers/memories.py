from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, List
import asyncpg
import logging

from app.auth.dependencies import require_subject
from app.db.client import get_db, get_optional_db
from app.db import repositories
from app.models.memory import MemoryFragment, MemoryPatch, DraftMemoryCreate, ConversationMemoryCreate, ConsentLevel
from uuid import uuid4
from app.services.memory_storage_service import MemoryStorageService
from app.models.session import SessionCreate, SessionStatus, SessionUpdate
from app.services.session_service import SessionService
from app.workers.index_memory import index_memory
from app.workers.sync_consent import sync_memory_consent

router = APIRouter(
    prefix='/memories', 
    tags=['memories'],
    dependencies=[Depends(require_subject)]
)

logger = logging.getLogger(__name__)


async def _index_memory(memory: MemoryFragment, user_id: str) -> None:
    await index_memory(memory.model_dump(mode="json"), user_id)


async def _import_fallback_memories(
    conn: asyncpg.Connection, user: dict,
) -> None:
    """Move pre-database fallback records into the authoritative tables.

    Earlier local runs could save an otherwise valid memory to private
    Supabase Storage while PostgreSQL was unreachable.  Once a database
    connection is restored, importing those records here preserves their
    original memory IDs and lets the normal idempotent Pinecone upsert index
    them.  A failed import must never make a user's memory list unavailable.
    """
    user_id = str(user["sub"])
    try:
        fallback_memories = await MemoryStorageService().list_memories(user_id)
    except Exception:
        logger.exception("Unable to read fallback memories for user %s", user_id)
        return

    if not fallback_memories:
        return

    session_service = SessionService(conn, user_id, user.get("email"))
    for fallback_memory in fallback_memories:
        if await repositories.get_memory(conn, fallback_memory.id, user_id):
            continue
        try:
            # A legacy storage record has no relational session.  Create an
            # owned completed session before importing it to satisfy the FK.
            session = await session_service.create_session(SessionCreate())
            # This historical record has no audio to process, so mark its
            # session complete without scheduling the audio post-processor.
            await conn.execute(
                "UPDATE sessions SET status = $1, ended_at = NOW() WHERE id = $2 AND user_id = $3",
                SessionStatus.COMPLETED, session.id, user_id,
            )
            imported = fallback_memory.model_copy(
                update={"session_id": session.id, "subject_id": user_id}
            )
            saved = await repositories.create_memory(conn, imported, user_id)
            await _index_memory(saved, user_id)
            logger.info("Imported fallback memory %s for user %s", saved.id, user_id)
        except Exception:
            # Continue with other records; re-running the list endpoint safely
            # retries an import because the original fallback object remains.
            logger.exception("Unable to import fallback memory %s", fallback_memory.id)

@router.post("/conversation", response_model=MemoryFragment, status_code=201)
async def save_conversation_memory(
    conversation: ConversationMemoryCreate,
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)],
):
    """Save a completed transcript as a private memory owned by the caller."""
    user_id = str(user["sub"])
    if conn is None:
        saved = await MemoryStorageService().save_conversation(user_id, conversation.content)
        await _index_memory(saved, user_id)
        return saved

    service = SessionService(conn, user_id, user.get("email"))
    session = await service.create_session(SessionCreate())
    memory = MemoryFragment(
        id=uuid4(), session_id=session.id, subject_id=session.subject_id,
        content=conversation.content, emotion_tags=["reflection"], topics=["voice-session"],
        people_mentioned=[], consent_level=ConsentLevel.PRIVATE, confidence_score=0.7,
    )
    saved = await repositories.create_memory(conn, memory, user_id)
    await _index_memory(saved, user_id)
    await service.update_session(str(session.id), SessionUpdate(status=SessionStatus.COMPLETED))
    return saved

@router.post("/draft", response_model=MemoryFragment, status_code=201)
async def create_draft_memory(
    draft: DraftMemoryCreate,
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
):
    session = await repositories.get_session(conn, draft.session_id, user["sub"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    memory = MemoryFragment(
        id=uuid4(), session_id=session.id, subject_id=session.subject_id,
        content=draft.content, emotion_tags=[draft.emotion], topics=[draft.topic],
        people_mentioned=draft.people, consent_level=ConsentLevel.PRIVATE,
        confidence_score=0.7,
    )
    saved = await repositories.create_memory(conn, memory, user["sub"])
    await _index_memory(saved, str(user["sub"]))
    return saved

@router.get("", response_model=List[MemoryFragment])
async def list_memories(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)]
):
    if conn is None:
        user_id = str(user["sub"])
        memories = await MemoryStorageService().list_memories(user_id)
        return memories
    # Import records saved while the old database connection was unavailable.
    # This is safe on every request because imports preserve memory IDs and the
    # database primary key prevents duplicates.
    await _import_fallback_memories(conn, user)
    subject_id = user.get("sub")
    memories = await repositories.list_memories(conn, subject_id)
    return memories

@router.patch("/{memory_id}", response_model=MemoryFragment)
async def update_memory_consent(
    memory_id: str,
    patch: MemoryPatch,
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)]
):
    subject_id = user.get("sub")
    if conn is None:
        try:
            updated = await MemoryStorageService().update_consent(str(subject_id), memory_id, patch.consent_level)
            await _index_memory(updated, str(subject_id))
            return updated
        except ValueError as error:
            raise HTTPException(status_code=404, detail="Memory not found") from error
    
    memory = await repositories.get_memory(conn, memory_id, subject_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    updated = await repositories.update_memory(conn, memory_id, subject_id, {"consent_level": patch.consent_level.value})
    if not updated:
        # The row could have been deleted after the owned read above.
        raise HTTPException(status_code=404, detail="Memory not found")
    
    await sync_memory_consent(str(updated.id), str(subject_id))

    return updated
