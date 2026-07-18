from fastapi import APIRouter, Depends
from typing import Annotated
from uuid import UUID, uuid4
from pydantic import BaseModel
import asyncpg

from app.auth.dependencies import get_current_user
from app.db.client import get_optional_db
from app.db import repositories
from app.models.session import SessionCreate
from app.services.realtime_service import GeminiLiveService
from app.services.session_service import SessionService

# Dedicated router for the specific /api/session/token path requested by the client
router = APIRouter(
    prefix='/api/session', 
    tags=['realtime'],
    dependencies=[Depends(get_current_user)]
)

def get_realtime_service() -> GeminiLiveService:
    return GeminiLiveService()


class RealtimeTokenRequest(BaseModel):
    session_id: UUID | None = None

@router.post("/token")
async def create_realtime_token(
    request: RealtimeTokenRequest,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection | None, Depends(get_optional_db)],
    service: Annotated[GeminiLiveService, Depends(get_realtime_service)],
):
    """
    Creates a constrained token for the Gemini Live WebSocket API.
    The browser receives only this short-lived token; the Gemini key remains server-side.
    """
    user_id = str(user["sub"])
    if request.session_id and conn:
        existing = await repositories.get_session(conn, str(request.session_id), user_id)
        if not existing:
            # Never mint an AI credential that purports to belong to someone
            # else's session.
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = str(existing.id)
    elif conn:
        # A durable, owner-scoped session is created before browser audio starts.
        created = await SessionService(conn, user_id, user.get("email")).create_session(SessionCreate())
        session_id = str(created.id)
    else:
        # Local development can still use Gemini Live plus transcript fallback
        # when direct Postgres is unavailable. This id is deliberately not
        # treated as an uploaded/processable recording session.
        session_id = str(request.session_id or uuid4())
    return await service.create_ephemeral_token(user_id, session_id)
