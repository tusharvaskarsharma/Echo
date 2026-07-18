from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Any

class ConsentLevel(StrEnum):
    PRIVATE = "private"
    FAMILY = "family"
    LEGACY = "legacy"

class MemoryFragment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    session_id: UUID | str
    subject_id: UUID | str
    content: str = Field(min_length=1)
    emotion_tags: list[str] = []
    topics: list[str] = []
    people_mentioned: list[str] = []
    time_period: str | None = None
    consent_level: ConsentLevel = ConsentLevel.FAMILY
    confidence_score: float = Field(ge=0, le=1)
    created_at: datetime | None = None
    # `search_document` is the exact semantic text sent to the embedding
    # provider. It is optional to preserve access to pre-schema memories.
    search_document: str | None = None
    semantic_metadata: dict[str, Any] = Field(default_factory=dict)

class MemoryPatch(BaseModel):
    consent_level: ConsentLevel

class DraftMemoryCreate(BaseModel):
    session_id: UUID | str
    content: str
    emotion: str
    topic: str
    people: list[str] = []

class ConversationMemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
