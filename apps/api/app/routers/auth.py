from fastapi import APIRouter, Depends
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me")
def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """
    Returns the decoded JWT claims for the currently authenticated user.
    """
    return {
        "user_id": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("app_metadata", {}).get("role", "authenticated")
    }

@router.get("/health/auth")
def auth_health():
    """
    Checks if Supabase Auth configuration is present and working.
    """
    settings = get_settings()
    is_configured = bool(settings.supabase_jwt_secret and settings.supabase_anon_key)
    return {
        "ok": True,
        "auth_configured": is_configured,
        "mode": "demo" if settings.demo_mode else "live"
    }
