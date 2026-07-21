from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Annotated
import asyncpg
import shutil
import tempfile
import os

from app.auth.dependencies import get_current_user
from app.db.client import get_db
from app.services.chat_service import ChatService
from app.models.emmy import ConverseResponse

router = APIRouter(
    prefix='/emmy',
    tags=['emmy'],
    dependencies=[Depends(get_current_user)]
)

async def require_legacy_contact(
    emmy_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)]
) -> str:
    user_id = user.get("sub")
    
    profile = await conn.fetchrow("SELECT subject_id, user_id FROM emmy_profiles WHERE id = $1", emmy_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Emmy profile not found")
    if str(profile["user_id"]) == str(user_id):
        return "owner"

    contact = await conn.fetchrow(
        "SELECT access_level FROM legacy_contacts WHERE subject_id = $1 AND user_id = $2 AND accepted_at IS NOT NULL",
        profile["subject_id"], user_id,
    )
    if not contact:
        raise HTTPException(status_code=403, detail="You do not have access to this family conversation")
    return contact["access_level"]

@router.post(
    "/{emmy_id}/converse",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def converse(
    emmy_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    access_level: Annotated[str, Depends(require_legacy_contact)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    text: str = Form(None),
    audio: UploadFile = File(None)
):
    chat_service = ChatService(conn)
    user_id = user.get("sub")
    
    audio_path = None
    if audio:
        suffix = os.path.splitext(audio.filename)[1] if audio.filename else ".m4a"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        shutil.copyfileobj(audio.file, tmp)
        tmp.close()
        audio_path = tmp.name
            
    # We don't try-finally remove audio path here easily because StreamingResponse is lazy.
    # The ChatService will read the audio immediately in converse_stream so we can delete it right after we get the generator.
    try:
        stream_gen = await chat_service.converse_stream(
            emmy_id=emmy_id,
            user_id=user_id,
            access_level=access_level,
            text=text,
            audio_path=audio_path
        )
        return StreamingResponse(
            stream_gen,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
