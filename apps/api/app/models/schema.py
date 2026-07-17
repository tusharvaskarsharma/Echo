from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class Profile(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Persona(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    date_of_birth: Optional[str] = None
    biography: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

class PersonaVersion(BaseModel):
    id: UUID
    persona_id: UUID
    provider_model_id: Optional[str] = None
    status: str
    training_data_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class VoiceProfile(BaseModel):
    id: UUID
    persona_id: UUID
    elevenlabs_voice_id: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class Session(BaseModel):
    id: UUID
    persona_id: UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime

class Memory(BaseModel):
    id: UUID
    persona_id: UUID
    session_id: Optional[UUID] = None
    content: str
    emotion_tags: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    people_mentioned: List[str] = Field(default_factory=list)
    consent_level: str
    confidence_score: Optional[float] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None

class MemoryChunk(BaseModel):
    id: UUID
    memory_id: UUID
    chunk_text: str
    chunk_index: int
    created_at: datetime

class Conversation(BaseModel):
    id: UUID
    persona_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    memory_ids: List[UUID] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    token_usage: Optional[int] = None
    created_at: datetime

class EmbeddingsMetadata(BaseModel):
    id: UUID
    persona_id: UUID
    memory_chunk_id: UUID
    pinecone_vector_id: str
    embedding_version: str
    created_at: datetime

class Upload(BaseModel):
    id: UUID
    persona_id: UUID
    session_id: Optional[UUID] = None
    file_path: str
    file_type: str
    file_size_bytes: Optional[int] = None
    created_at: datetime

class ProcessingJob(BaseModel):
    id: UUID
    job_type: str
    target_id: UUID
    status: str
    result: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AuditLog(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    entity_type: str
    entity_id: UUID
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
