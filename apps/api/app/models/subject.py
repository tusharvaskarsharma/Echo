from datetime import datetime, date
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class Subject(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    full_name: str
    email: str
    date_of_birth: date
    created_at: datetime | None = None
    updated_at: datetime | None = None
