from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class FinetuneJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    subject_id: UUID | str
    provider_job_id: str | None = None
    provider_file_id: str | None = None
    status: str
    cost_usd: float | None = None
    duration_seconds: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class FinetuneStatus(BaseModel):
    subject_id: str
    enabled: bool
    model_id: str | None = None
    training_examples: int
    latest_job: FinetuneJob | None = None
