from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, List
import asyncpg

from app.auth.dependencies import require_subject
from app.db.client import get_db, get_optional_db
from app.db import repositories
from app.models.memory import MemoryFragment, MemoryPatch, DraftMemoryCreate, ConsentLevel
from uuid import uuid4
from app.services.pinecone_service import PineconeService

router = APIRouter(
    prefix='/memories', 
    tags=['memories'],
    dependencies=[Depends(require_subject)]
)

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
        # The caller is authenticated, but the local API has no direct
        # PostgreSQL connection.  An empty list is the safe dashboard state:
        # it exposes no other user's data and avoids an internal-server error.
        return []
    subject_id = user.get("sub")
    memories = await repositories.list_memories(conn, subject_id)
    return memories

@router.patch("/{memory_id}", response_model=MemoryFragment)
async def update_memory_consent(
    memory_id: str,
    patch: MemoryPatch,
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
):
    subject_id = user.get("sub")
    
    memory = await repositories.get_memory(conn, memory_id, subject_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    updated = await repositories.update_memory(conn, memory_id, subject_id, {"consent_level": patch.consent_level.value})
    
    try:
        pinecone_service = PineconeService()
        pinecone_service.update_metadata(str(subject_id), memory_id, {"consent_level": patch.consent_level.value})
    except Exception as e:
        print(f"Failed to sync pinecone: {e}")
        
    return updated
