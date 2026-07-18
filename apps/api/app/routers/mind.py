"""Owner-scoped Mind Model construction and retrieval."""

import json
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_subject
from app.db.client import get_db
from app.models.mind_model import MindModelOutput, StructuredMemoryInput
from app.services.mind_model_builder import MindModelBuilderService


router = APIRouter(prefix="/mind", tags=["mind"], dependencies=[Depends(require_subject)])


@router.post("/build", response_model=MindModelOutput)
async def build_mind_model(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> MindModelOutput:
    """Build a draft-only model from the caller's own structured memories."""
    user_id = str(user["sub"])
    rows = await conn.fetch("""
        SELECT id, content, semantic_metadata, topics, people_mentioned, emotion_tags, time_period
        FROM memories WHERE user_id = $1 ORDER BY created_at ASC
    """, user_id)
    memories = [StructuredMemoryInput(
        id=str(row["id"]), content=row["content"],
        semantic_metadata=row["semantic_metadata"] or {}, topics=row["topics"] or [],
        people_mentioned=row["people_mentioned"] or [], emotion_tags=row["emotion_tags"] or [],
        time_period=row["time_period"],
    ) for row in rows]
    model = await MindModelBuilderService().build(memories)

    async with conn.transaction():
        await conn.execute("""
            INSERT INTO subjects (id, user_id, full_name, email, date_of_birth)
            VALUES ($1, $1, $2, $3, NULL)
            ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id
        """, user_id, "My Legacy", user.get("email") or f"{user_id}@account.local")
        profile = await conn.fetchrow("""
            INSERT INTO mind_profiles (user_id, subject_id, model_status, summary, last_processed_at)
            VALUES ($1, $1, 'draft', $2, now())
            ON CONFLICT (user_id) DO UPDATE SET
                subject_id = EXCLUDED.subject_id,
                summary = EXCLUDED.summary,
                last_processed_at = now()
            WHERE mind_profiles.model_status <> 'revoked'
            RETURNING id
        """, user_id, model.mind_summary or None)
        if not profile:
            raise HTTPException(status_code=403, detail="The Mind Model has been revoked for this account")
        await conn.execute("""
            INSERT INTO mind_model_snapshots (mind_profile_id, user_id, source_memory_ids, model)
            VALUES ($1, $2, $3::jsonb, $4::jsonb)
        """, profile["id"], user_id, json.dumps([memory.id for memory in memories]), json.dumps(model.model_dump(mode="json")))
    return model


@router.get("/latest", response_model=MindModelOutput | None)
async def latest_mind_model(
    user: Annotated[dict, Depends(require_subject)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> MindModelOutput | None:
    row = await conn.fetchrow("""
        SELECT snapshot.model FROM mind_model_snapshots AS snapshot
        WHERE snapshot.user_id = $1 ORDER BY snapshot.created_at DESC LIMIT 1
    """, user["sub"])
    return MindModelOutput.model_validate(row["model"]) if row else None
