from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, List
import asyncpg

from app.auth.dependencies import require_subject
from app.db.client import get_db, get_optional_db
from app.db import repositories
from app.models.memory import MemoryFragment, MemoryPatch, DraftMemoryCreate, ConversationMemoryCreate, ConsentLevel
from uuid import uuid4
from app.services.memory_storage_service import MemoryStorageService
from app.models.session import SessionCreate, SessionStatus, SessionUpdate
from app.services.session_service import SessionService
from app.workers.task_runner import run_task

router = APIRouter(
    prefix='/memories', 
    tags=['memories'],
    dependencies=[Depends(require_subject)]
)

@router.post("/conversation", response_model=MemoryFragment, status_code=201)
async def save_conversation_memory(
    conversation: ConversationMemoryCreate,
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)],
):
    """Save a completed transcript as a private memory owned by the caller."""
    user_id = str(user["sub"])
    if conn is None:
        return await MemoryStorageService().save_conversation(user_id, conversation.content)

    service = SessionService(conn, user_id, user.get("email"))
    session = await service.create_session(SessionCreate())
    memory = MemoryFragment(
        id=uuid4(), session_id=session.id, subject_id=session.subject_id,
        content=conversation.content, emotion_tags=["reflection"], topics=["voice-session"],
        people_mentioned=[], consent_level=ConsentLevel.PRIVATE, confidence_score=0.7,
    )
    saved = await repositories.create_memory(conn, memory, user_id)
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
    return await repositories.create_memory(conn, memory, user["sub"])

@router.get("", response_model=List[MemoryFragment])
async def list_memories(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)]
):
    if conn is None:
        return await MemoryStorageService().list_memories(str(user["sub"]))
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
            return await MemoryStorageService().update_consent(str(subject_id), memory_id, patch.consent_level)
        except ValueError as error:
            raise HTTPException(status_code=404, detail="Memory not found") from error
    
    memory = await repositories.get_memory(conn, memory_id, subject_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    updated = await repositories.update_memory(conn, memory_id, subject_id, {"consent_level": patch.consent_level.value})
    if not updated:
        # The row could have been deleted after the owned read above.
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # PostgreSQL is now authoritative and the HTTP response is intentionally
    # not coupled to Pinecone availability. The worker re-reads this owned row
    # before updating the matching vector's consent metadata.
    try:
        run_task("sync_memory_consent", str(updated.id), str(subject_id))
    except Exception:
        # A broker outage must not lie about the durable privacy change. The
        # error is logged by the task dispatcher; a queue monitor can retry it.
        import logging
        logging.getLogger(__name__).exception("Unable to dispatch Pinecone consent synchronization")

    return updated
