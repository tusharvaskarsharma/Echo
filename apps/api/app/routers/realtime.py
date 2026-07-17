from fastapi import APIRouter, Depends
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.services.realtime_service import GeminiLiveService

# Dedicated router for the specific /api/session/token path requested by the client
router = APIRouter(
    prefix='/api/session', 
    tags=['realtime'],
    dependencies=[Depends(get_current_user)]
)

def get_realtime_service() -> GeminiLiveService:
    return GeminiLiveService()

@router.post("/token")
async def create_realtime_token(
    user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[GeminiLiveService, Depends(get_realtime_service)],
):
    """
    Creates a constrained token for the Gemini Live WebSocket API.
    The browser receives only this short-lived token; the Gemini key remains server-side.
    """
    return await service.create_ephemeral_token(str(user["sub"]))
