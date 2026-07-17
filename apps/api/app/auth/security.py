import logging

import httpx
import jwt
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


def _validate_with_supabase(token: str) -> dict:
    """Validate a bearer session through Supabase Auth when local JWT checks fail.

    This supports Supabase signing-key rotation and asymmetric signing without
    accepting an unverified token locally.
    """
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.RequestError as error:
        logger.error("Supabase session validation request failed: %s", error)
        raise HTTPException(status_code=503, detail="Authentication validation is temporarily unavailable")

    if response.status_code != 200:
        logger.warning("Supabase rejected a bearer session with status %s", response.status_code)
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please sign in again.")

    user = response.json()
    return {
        "sub": user["id"],
        "email": user.get("email"),
        "app_metadata": user.get("app_metadata", {}),
        "user_metadata": user.get("user_metadata", {}),
    }


def verify_jwt_token(token: str) -> dict:
    """Securely validate a Supabase access token and return its user claims."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            options={"verify_aud": True, "verify_iss": True},
        )
        if not payload.get("sub"):
            raise jwt.InvalidTokenError("JWT has no subject")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session has expired. Please sign in again.")
    except jwt.InvalidTokenError as error:
        # Supabase validates the token remotely if its project has rotated away
        # from the configured legacy HS256 secret or uses asymmetric keys.
        logger.info("Local JWT verification failed (%s); checking Supabase Auth", error)
        return _validate_with_supabase(token)
