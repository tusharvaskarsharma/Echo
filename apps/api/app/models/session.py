from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List

class SessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Session(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    subject_id: UUID | str
    status: SessionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    audio_url: str | None = None
    transcript: str | None = None
    transcript_segments: list[dict] = []
    created_at: datetime | None = None

class SessionCreate(BaseModel):
    # Subject ID is inferred from the authenticated user, but we can allow passing it if needed.
    # The requirements say "Associate every session with the authenticated subject." 
    # So we don't need input fields for creation unless there's a title (though DB doesn't have a title column in migrations).
    pass

class SessionUpdate(BaseModel):
    status: SessionStatus


class SessionTranscriptUpdate(BaseModel):
    """The browser's complete Emmy/User conversation, before audio processing."""
    transcript: str

class PaginatedSessionResponse(BaseModel):
    items: List[Session]
    total: int
    limit: int
    offset: int
