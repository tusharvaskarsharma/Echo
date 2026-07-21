from uuid import UUID, uuid4
from datetime import datetime, timezone
import asyncpg
import logging
from fastapi import HTTPException
from app.models.session import Session, SessionStatus, SessionCreate, SessionUpdate, PaginatedSessionResponse
from app.db import repositories
from app.workers.process_session import process_session
from app.services.session_audio_storage_service import SessionAudioStorageService

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, conn: asyncpg.Connection, subject_id: str | UUID, email: str | None = None):
        self.conn = conn
        self.subject_id = str(subject_id)
        self.email = email or f"{subject_id}@account.local"

    async def _ensure_subject(self) -> None:
        # Each account gets a private default subject for the existing interview flow.
        await self.conn.execute("INSERT INTO subjects (id, user_id, full_name, email, date_of_birth) VALUES ($1, $1, $2, $3, NULL) ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id", self.subject_id, "My Legacy", self.email)

    async def create_session(self, req: SessionCreate) -> Session:
        await self._ensure_subject()
        now = datetime.now(timezone.utc)
        session = Session(
            id=str(uuid4()),
            subject_id=self.subject_id,
            status=SessionStatus.ACTIVE,
            started_at=now,
            ended_at=None,
            created_at=now
        )
        return await repositories.create_session(self.conn, session, self.subject_id)

    async def get_session(self, session_id: str) -> Session:
        session = await repositories.get_session(self.conn, session_id, self.subject_id)
        if not session:
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
            
        should_process = (req.status == SessionStatus.COMPLETED and session.status != SessionStatus.COMPLETED)
            
        session.status = req.status
        updated_session = await repositories.update_session(self.conn, session, self.subject_id)
        
        if should_process:
            await process_session(str(session.id))
            logger.info(f"Completed process_session for session {session.id}")
                
        return updated_session

    async def save_audio(self, session_id: str, content: bytes, content_type: str) -> Session:
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded recording is empty")
        session = await self.get_session(session_id)
        audio_url = await SessionAudioStorageService().upload(
            self.subject_id, str(session.id), content, content_type,
        )
        updated = await repositories.update_session_audio_url(
            self.conn, session.id, self.subject_id, audio_url,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        return updated

    async def save_transcript(self, session_id: str, transcript: str) -> Session:
        """Store both Emmy prompts and the user's answers as canonical evidence."""
        cleaned = transcript.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="The session transcript is empty")
        if len(cleaned) > 250_000:
            raise HTTPException(status_code=413, detail="The session transcript exceeds the 250,000 character limit")
        await self.get_session(session_id)
        updated = await repositories.update_session_transcript(
            self.conn, session_id, self.subject_id, cleaned,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        return updated

    async def delete_session(self, session_id: str) -> None:
        await self.get_session(session_id) # Validates ownership and existence
        success = await repositories.delete_session(self.conn, session_id, self.subject_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete session")
