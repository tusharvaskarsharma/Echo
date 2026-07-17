from fastapi import APIRouter, Depends
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.services.realtime_service import RealtimeService

# Dedicated router for the specific /api/session/token path requested by the client
router = APIRouter(
    prefix='/api/session', 
    tags=['realtime'],
    dependencies=[Depends(get_current_user)]
)

def get_realtime_service() -> RealtimeService:
    return RealtimeService()

@router.post("/token")
async def create_realtime_token(
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[RealtimeService, Depends(get_realtime_service)],
):
    """
    Creates an ephemeral session token for the OpenAI Realtime API.
    The frontend uses this token to establish a WebRTC connection directly to OpenAI,
    keeping our server's API key strictly secret.
    """
    return await service.create_ephemeral_token(str(user["sub"]))
