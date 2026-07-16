from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, List
import asyncpg

from app.auth.dependencies import require_subject
from app.db.client import get_db
from app.db import repositories
from app.models.memory import MemoryFragment, MemoryPatch
from app.services.pinecone_service import PineconeService

router = APIRouter(
    prefix='/memories', 
    tags=['memories'],
    dependencies=[Depends(require_subject)]
)

@router.get("", response_model=List[MemoryFragment])
async def list_memories(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
):
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
    
    memory = await repositories.get_memory(conn, memory_id)
    if not memory or str(memory.subject_id) != subject_id:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    updated = await repositories.update_memory(conn, memory_id, {"consent_level": patch.consent_level.value})
    
    try:
        pinecone_service = PineconeService()
        pinecone_service.update_metadata(memory_id, {"consent_level": patch.consent_level.value})
    except Exception as e:
        print(f"Failed to sync pinecone: {e}")
        
    return updated
