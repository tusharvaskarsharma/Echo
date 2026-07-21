from .schema import (
    Profile,
    Persona,
    PersonaVersion,
    VoiceProfile,
    Session as NewSession,
    Memory as NewMemory,
    MemoryChunk,
    Conversation,
    Message,
    EmbeddingsMetadata,
    Upload,
    ProcessingJob,
    AuditLog
)

from .subject import Subject
from .session import Session, SessionCreate, SessionUpdate, PaginatedSessionResponse
from .memory import MemoryFragment, MemoryPatch, DraftMemoryCreate
from .emmy import EmmyProfile, ConversationHistory, LegacyContact
from .finetune import FinetuneJob
from .identity import IdentityProfileResponse, IdentityProfileUpdate, IdentityPrivacySettings

# Keep some compatibility for old imports if needed during transition, though it's better to update imports.
