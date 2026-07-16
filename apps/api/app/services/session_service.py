from uuid import UUID, uuid4
from datetime import datetime, timezone
import asyncpg
import logging
from fastapi import HTTPException
from app.models.session import Session, SessionStatus, SessionCreate, SessionUpdate, PaginatedSessionResponse
from app.db import repositories
from app.workers.task_runner import run_task

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, conn: asyncpg.Connection, subject_id: str | UUID):
        self.conn = conn
        self.subject_id = str(subject_id)

    async def create_session(self, req: SessionCreate) -> Session:
        now = datetime.now(timezone.utc)
        session = Session(
            id=str(uuid4()),
            subject_id=self.subject_id,
            status=SessionStatus.ACTIVE,
            started_at=now,
            ended_at=None,
            created_at=now
        )
        return await repositories.create_session(self.conn, session)

    async def get_session(self, session_id: str) -> Session:
        session = await repositories.get_session(self.conn, session_id)
        if not session or str(session.subject_id) != self.subject_id:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    async def list_sessions(self, limit: int, offset: int) -> PaginatedSessionResponse:
        items, total = await repositories.list_sessions(self.conn, self.subject_id, limit, offset)
        return PaginatedSessionResponse(items=items, total=total, limit=limit, offset=offset)

    async def update_session(self, session_id: str, req: SessionUpdate) -> Session:
        session = await self.get_session(session_id)
        
        # Automatically update timestamps based on state transitions
        if req.status in [SessionStatus.COMPLETED, SessionStatus.CANCELLED] and session.status not in [SessionStatus.COMPLETED, SessionStatus.CANCELLED]:
            session.ended_at = datetime.now(timezone.utc)
            
        # Trigger Celery worker if transitioning to COMPLETED
        trigger_worker = (req.status == SessionStatus.COMPLETED and session.status != SessionStatus.COMPLETED)
            
        session.status = req.status
        updated_session = await repositories.update_session(self.conn, session)
        
        if trigger_worker:
            try:
                # Fire and forget
                run_task("process_session", str(session.id))
                logger.info(f"Triggered process_session for session {session.id}")
            except Exception as e:
                logger.error(f"Failed to trigger process_session: {e}")
                
        return updated_session

    async def delete_session(self, session_id: str) -> None:
        await self.get_session(session_id) # Validates ownership and existence
        success = await repositories.delete_session(self.conn, session_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete session")
