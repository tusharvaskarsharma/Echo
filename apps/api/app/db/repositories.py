import json
import asyncpg
from typing import List, Optional
from uuid import UUID

from app.models import (
    Subject, Session, MemoryFragment, EchoProfile, 
    LegacyContact, ConversationHistory
)
from app.models.finetune import FinetuneJob

async def create_subject(conn: asyncpg.Connection, subject: Subject) -> Subject:
    query = """
    INSERT INTO subjects (id, full_name, email, date_of_birth)
    VALUES ($1, $2, $3, $4)
    RETURNING id, full_name, email, date_of_birth, created_at, updated_at
    """
    row = await conn.fetchrow(
        query, subject.id, subject.full_name, subject.email, subject.date_of_birth
    )
    return Subject(**dict(row))

async def get_subject(conn: asyncpg.Connection, subject_id: UUID | str) -> Optional[Subject]:
    query = "SELECT * FROM subjects WHERE id = $1"
    row = await conn.fetchrow(query, subject_id)
    return Subject(**dict(row)) if row else None

async def create_session(conn: asyncpg.Connection, session: Session, user_id: UUID | str) -> Session:
    query = """
    INSERT INTO sessions (id, subject_id, user_id, status, started_at, ended_at)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id, subject_id, status, started_at, ended_at, created_at
    """
    row = await conn.fetchrow(
        query, session.id, session.subject_id, user_id, session.status, session.started_at, session.ended_at
    )
    return Session(**dict(row))

async def get_session(conn: asyncpg.Connection, session_id: UUID | str, user_id: UUID | str | None = None) -> Optional[Session]:
    """Fetch an owned session; worker code may omit ownership after a trusted job is queued."""
    if user_id is None:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    else:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1 AND user_id = $2", session_id, user_id)
    return Session(**dict(row)) if row else None

async def list_sessions(conn: asyncpg.Connection, user_id: UUID | str, limit: int = 10, offset: int = 0) -> tuple[list[Session], int]:
    total = await conn.fetchval("SELECT COUNT(*) FROM sessions WHERE user_id = $1", user_id)
    
    query = """
    SELECT * FROM sessions WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT $2 OFFSET $3
    """
    rows = await conn.fetch(query, user_id, limit, offset)
    items = [Session(**dict(row)) for row in rows]
    return items, total

async def update_session(conn: asyncpg.Connection, session: Session, user_id: UUID | str) -> Session:
    query = """
    UPDATE sessions SET status = $1, ended_at = $2
    WHERE id = $3 AND user_id = $4
    RETURNING *
    """
    row = await conn.fetchrow(query, session.status, session.ended_at, session.id, user_id)
    return Session(**dict(row)) if row else session


async def update_session_audio_url(conn: asyncpg.Connection, session_id: UUID | str, user_id: UUID | str, audio_url: str) -> Session | None:
    row = await conn.fetchrow(
        "UPDATE sessions SET audio_url = $1 WHERE id = $2 AND user_id = $3 RETURNING *",
        audio_url, session_id, user_id,
    )
    return Session(**dict(row)) if row else None

async def delete_session(conn: asyncpg.Connection, session_id: UUID | str, user_id: UUID | str) -> bool:
    result = await conn.execute("DELETE FROM sessions WHERE id = $1 AND user_id = $2", session_id, user_id)
    return result == "DELETE 1"


async def create_memory(conn: asyncpg.Connection, memory: MemoryFragment, user_id: UUID | str | None = None) -> MemoryFragment:
    # Processing workers receive only a session id. Derive its owner server-side
    # rather than accepting an untrusted owner field from a job payload.
    owner_id = user_id or await conn.fetchval("SELECT user_id FROM sessions WHERE id = $1", memory.session_id)
    if not owner_id:
        raise ValueError("Cannot create a memory without an owning user")
    query = """
    INSERT INTO memories (id, session_id, subject_id, user_id, content, emotion_tags, topics, people_mentioned, consent_level, confidence_score, time_period)
    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, $9, $10, $11)
    RETURNING *
    """
    row = await conn.fetchrow(
        query, 
        memory.id, memory.session_id, memory.subject_id, owner_id, memory.content,
        json.dumps(memory.emotion_tags), json.dumps(memory.topics),
        json.dumps(memory.people_mentioned), memory.consent_level, memory.confidence_score, memory.time_period
    )
    if row:
        row_dict = dict(row)
        # Parse JSONB fields back to python lists
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        return MemoryFragment(**row_dict)
    return None

async def get_memory(conn: asyncpg.Connection, memory_id: UUID | str, user_id: UUID | str) -> Optional[MemoryFragment]:
    row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1 AND user_id = $2", memory_id, user_id)
    if row:
        row_dict = dict(row)
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        return MemoryFragment(**row_dict)
    return None

async def create_conversation_history(conn: asyncpg.Connection, history: ConversationHistory) -> ConversationHistory:
    query = """
    INSERT INTO conversation_history (id, echo_profile_id, user_id, question, response, memory_ids, latency_ms, token_usage)
    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
    RETURNING *
    """
    row = await conn.fetchrow(
        query,
        history.id, history.echo_profile_id, history.user_id, history.question,
        history.response, json.dumps(history.memory_ids), history.latency_ms, history.token_usage
    )
    if row:
        row_dict = dict(row)
        row_dict['memory_ids'] = json.loads(row_dict['memory_ids']) if isinstance(row_dict['memory_ids'], str) else row_dict['memory_ids']
        return ConversationHistory(**row_dict)
    return None

async def list_memories(conn: asyncpg.Connection, user_id: UUID | str) -> List[MemoryFragment]:
    rows = await conn.fetch("SELECT * FROM memories WHERE user_id = $1 ORDER BY created_at DESC", user_id)
    memories = []
    for row in rows:
        row_dict = dict(row)
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        memories.append(MemoryFragment(**row_dict))
    return memories

async def update_memory(conn: asyncpg.Connection, memory_id: UUID | str, user_id: UUID | str, updates: dict) -> Optional[MemoryFragment]:
    set_clauses = []
    values = []
    for i, (k, v) in enumerate(updates.items()):
        set_clauses.append(f"{k} = ${i+1}")
        values.append(v)
    
    if not set_clauses:
        return await get_memory(conn, memory_id, user_id)
        
    query = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ${len(values)+1} AND user_id = ${len(values)+2} RETURNING *"
    values.append(memory_id)
    values.append(user_id)
    
    row = await conn.fetchrow(query, *values)
    if row:
        row_dict = dict(row)
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        return MemoryFragment(**row_dict)
    return None

async def create_finetune_job(conn: asyncpg.Connection, job: FinetuneJob) -> FinetuneJob:
    user_id = await conn.fetchval("SELECT user_id FROM subjects WHERE id = $1", job.subject_id)
    if not user_id:
        raise ValueError("Cannot create a fine-tuning job without an owning user")
    query = """
    INSERT INTO finetune_jobs (id, subject_id, user_id, provider_job_id, provider_file_id, status)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING *
    """
    row = await conn.fetchrow(query, job.id, job.subject_id, user_id, job.provider_job_id, job.provider_file_id, job.status)
    return FinetuneJob(**dict(row)) if row else None

async def update_finetune_job(conn: asyncpg.Connection, job_id: UUID | str, updates: dict) -> FinetuneJob | None:
    set_clauses = []
    values = []
    for i, (k, v) in enumerate(updates.items()):
        set_clauses.append(f"{k} = ${i+1}")
        values.append(v)
    
    if not set_clauses:
        return None
        
    set_clauses.append(f"updated_at = NOW()")
    query = f"UPDATE finetune_jobs SET {', '.join(set_clauses)} WHERE id = ${len(values)+1} RETURNING *"
    values.append(job_id)
    
    row = await conn.fetchrow(query, *values)
    return FinetuneJob(**dict(row)) if row else None

async def get_latest_finetune_job(conn: asyncpg.Connection, subject_id: UUID | str) -> FinetuneJob | None:
    query = "SELECT * FROM finetune_jobs WHERE subject_id = $1 ORDER BY created_at DESC LIMIT 1"
    row = await conn.fetchrow(query, subject_id)
    return FinetuneJob(**dict(row)) if row else None
