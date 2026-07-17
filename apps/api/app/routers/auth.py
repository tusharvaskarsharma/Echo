from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import httpx

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
        "mode": "live"
    }

@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: Annotated[dict, Depends(get_current_user)]):
    """Deletes the authenticated user through Supabase Auth, cascading owned rows."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(503, "Account deletion is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{current_user['sub']}", headers={"apikey": settings.supabase_service_role_key, "Authorization": f"Bearer {settings.supabase_service_role_key}"})
    if response.status_code not in (200, 204):
        raise HTTPException(502, "Unable to delete account")
