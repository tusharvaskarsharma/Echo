from fastapi import APIRouter, Depends, Query, status
from typing import Annotated
import asyncpg

from app.auth.dependencies import require_subject
from app.db.client import get_db
from app.models.session import Session, SessionCreate, SessionUpdate, PaginatedSessionResponse
from app.services.session_service import SessionService

# Protect all routes by requiring the subject role
router = APIRouter(
    prefix='/sessions', 
    tags=['sessions'],
    dependencies=[Depends(require_subject)]
)

def get_session_service(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
) -> SessionService:
    """Dependency to inject the SessionService with the current user's DB connection."""
    subject_id = user.get("sub")
    return SessionService(conn, subject_id)

@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: SessionCreate,
    service: Annotated[SessionService, Depends(get_session_service)]
):
    """Creates a new interview session for the authenticated subject."""
    return await service.create_session(req)

@router.get("", response_model=PaginatedSessionResponse)
async def list_sessions(
    service: Annotated[SessionService, Depends(get_session_service)],
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Retrieves a paginated list of sessions for the authenticated subject."""
    return await service.list_sessions(limit, offset)

@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    service: Annotated[SessionService, Depends(get_session_service)]
):
    """Retrieves a specific session belonging to the authenticated subject."""
    return await service.get_session(session_id)

@router.patch("/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    req: SessionUpdate,
    service: Annotated[SessionService, Depends(get_session_service)]
):
    """Updates a session's state and timestamps."""
    return await service.update_session(session_id, req)

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    service: Annotated[SessionService, Depends(get_session_service)]
):
    """Hard deletes a session."""
    await service.delete_session(session_id)
