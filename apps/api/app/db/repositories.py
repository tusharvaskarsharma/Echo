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

async def create_session(conn: asyncpg.Connection, session: Session) -> Session:
    query = """
    INSERT INTO sessions (id, subject_id, status, started_at, ended_at)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id, subject_id, status, started_at, ended_at, created_at
    """
    row = await conn.fetchrow(
        query, session.id, session.subject_id, session.status, session.started_at, session.ended_at
    )
    return Session(**dict(row))

async def get_session(conn: asyncpg.Connection, session_id: UUID | str) -> Optional[Session]:
    query = "SELECT * FROM sessions WHERE id = $1"
    row = await conn.fetchrow(query, session_id)
    return Session(**dict(row)) if row else None

async def list_sessions(conn: asyncpg.Connection, subject_id: UUID | str, limit: int = 10, offset: int = 0) -> tuple[list[Session], int]:
    count_query = "SELECT COUNT(*) FROM sessions WHERE subject_id = $1"
    total = await conn.fetchval(count_query, subject_id)
    
    query = """
    SELECT * FROM sessions WHERE subject_id = $1
    ORDER BY created_at DESC
    LIMIT $2 OFFSET $3
    """
    rows = await conn.fetch(query, subject_id, limit, offset)
    items = [Session(**dict(row)) for row in rows]
    return items, total

async def update_session(conn: asyncpg.Connection, session: Session) -> Session:
    query = """
    UPDATE sessions SET status = $1, ended_at = $2
    WHERE id = $3
    RETURNING *
    """
    row = await conn.fetchrow(query, session.status, session.ended_at, session.id)
    return Session(**dict(row)) if row else session

async def delete_session(conn: asyncpg.Connection, session_id: UUID | str) -> bool:
    query = "DELETE FROM sessions WHERE id = $1"
    result = await conn.execute(query, session_id)
    return result == "DELETE 1"


async def create_memory(conn: asyncpg.Connection, memory: MemoryFragment) -> MemoryFragment:
    query = """
    INSERT INTO memories (id, session_id, subject_id, content, emotion_tags, topics, people_mentioned, consent_level, confidence_score)
    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9)
    RETURNING *
    """
    row = await conn.fetchrow(
        query, 
        memory.id, memory.session_id, memory.subject_id, memory.content, 
        json.dumps(memory.emotion_tags), json.dumps(memory.topics), 
        json.dumps(memory.people_mentioned), memory.consent_level, memory.confidence_score
    )
    if row:
        row_dict = dict(row)
        # Parse JSONB fields back to python lists
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        return MemoryFragment(**row_dict)
    return None

async def get_memory(conn: asyncpg.Connection, memory_id: UUID | str) -> Optional[MemoryFragment]:
    query = "SELECT * FROM memories WHERE id = $1"
    row = await conn.fetchrow(query, memory_id)
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

async def list_memories(conn: asyncpg.Connection, subject_id: UUID | str) -> List[MemoryFragment]:
    query = "SELECT * FROM memories WHERE subject_id = $1 ORDER BY created_at DESC"
    rows = await conn.fetch(query, subject_id)
    memories = []
    for row in rows:
        row_dict = dict(row)
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        memories.append(MemoryFragment(**row_dict))
    return memories

async def update_memory(conn: asyncpg.Connection, memory_id: UUID | str, updates: dict) -> Optional[MemoryFragment]:
    set_clauses = []
    values = []
    for i, (k, v) in enumerate(updates.items()):
        set_clauses.append(f"{k} = ${i+1}")
        values.append(v)
    
    if not set_clauses:
        return await get_memory(conn, memory_id)
        
    query = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ${len(values)+1} RETURNING *"
    values.append(memory_id)
    
    row = await conn.fetchrow(query, *values)
    if row:
        row_dict = dict(row)
        row_dict['emotion_tags'] = json.loads(row_dict['emotion_tags']) if isinstance(row_dict['emotion_tags'], str) else row_dict['emotion_tags']
        row_dict['topics'] = json.loads(row_dict['topics']) if isinstance(row_dict['topics'], str) else row_dict['topics']
        row_dict['people_mentioned'] = json.loads(row_dict['people_mentioned']) if isinstance(row_dict['people_mentioned'], str) else row_dict['people_mentioned']
        return MemoryFragment(**row_dict)
    return None

async def create_finetune_job(conn: asyncpg.Connection, job: FinetuneJob) -> FinetuneJob:
    query = """
    INSERT INTO finetune_jobs (id, subject_id, openai_job_id, openai_file_id, status)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING *
    """
    row = await conn.fetchrow(query, job.id, job.subject_id, job.openai_job_id, job.openai_file_id, job.status)
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
