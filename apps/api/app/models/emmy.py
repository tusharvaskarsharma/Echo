from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from .memory import ConsentLevel

class EmmyProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    subject_id: UUID | str
    fine_tuned_model: str | None = None
    voice_preset: str | None = None
    created_at: datetime | None = None

class LegacyContact(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    subject_id: UUID | str
    user_id: UUID | str
    access_level: str
    invited_at: datetime | None = None
    accepted_at: datetime | None = None

class ConversationHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    emmy_profile_id: UUID | str
    user_id: UUID | str
    question: str
    response: str
    memory_ids: list[str] = []
    latency_ms: int
    token_usage: int
    created_at: datetime | None = None

class Citation(BaseModel):
    memory_id: str
    excerpt: str
    session_id: str
    timestamp: str

class ConverseResponse(BaseModel):
    response: str
    sources: list[Citation]
