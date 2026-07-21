from fastapi import APIRouter, Depends
from typing import Annotated
import asyncpg
from app.auth.dependencies import require_subject
from app.db.client import get_db
from app.db import repositories
from app.models.finetune import FinetuneStatus

router = APIRouter(
    prefix='/finetune', 
    tags=['finetune'],
    dependencies=[Depends(require_subject)]
)

@router.get("/status", response_model=FinetuneStatus)
async def get_finetune_status(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
):
    subject_id = user.get("sub")
    
    # Check eligibility
    sessions_count = await conn.fetchval("SELECT count(*) FROM sessions WHERE user_id = $1 AND status = 'completed'", subject_id)
    memories_count = await conn.fetchval("SELECT count(*) FROM memories WHERE user_id = $1", subject_id)
    
    enabled = (sessions_count >= 3) and (memories_count >= 150)
    
    # Get active model
    profile = await conn.fetchrow("SELECT fine_tuned_model FROM emmy_profiles WHERE user_id = $1", subject_id)
    model_id = profile["fine_tuned_model"] if profile else None
    
    latest_job = await repositories.get_latest_finetune_job(conn, subject_id)
    
    return FinetuneStatus(
        subject_id=str(subject_id),
        enabled=enabled,
        model_id=model_id,
        training_examples=memories_count,
        latest_job=latest_job
    )
