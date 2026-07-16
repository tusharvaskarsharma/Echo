from fastapi import APIRouter, Request
import json
import asyncpg
from typing import Annotated
from fastapi import Depends
from app.db.client import get_db

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post("/openai")
async def openai_webhook(
    request: Request,
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
):
    # In production, verify the webhook signature.
    try:
        body = await request.json()
    except:
        return {"status": "ignored"}
    
    # Listen for fine tuning completion
    if body.get("type") == "fine_tuning.job.succeeded":
        data = body.get("data", {})
        job_id = data.get("id")
        fine_tuned_model = data.get("fine_tuned_model")
        
        if job_id and fine_tuned_model:
            # 1. Update job status
            await conn.execute("UPDATE finetune_jobs SET status = 'completed' WHERE openai_job_id = $1", job_id)
            
            # 2. Find subject
            subject_id = await conn.fetchval("SELECT subject_id FROM finetune_jobs WHERE openai_job_id = $1", job_id)
            
            if subject_id:
                # 3. Update echo profile directly
                await conn.execute(
                    "UPDATE echo_profiles SET fine_tuned_model = $1 WHERE subject_id = $2",
                    fine_tuned_model, subject_id
                )
    
    return {"status": "ok"}
