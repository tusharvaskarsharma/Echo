import jwt
import logging
from fastapi import HTTPException
from app.config import get_settings

logger = logging.getLogger(__name__)

def verify_jwt_token(token: str) -> dict:
    """
    Verifies a Supabase JWT token using the Supabase JWT Secret.
    Returns the decoded payload if valid.
    """
    settings = get_settings()
    
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="Supabase JWT secret not configured.")

    try:
        # Decode the token
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None,
            options={"verify_aud": True, "verify_iss": bool(settings.supabase_url)},
        )
        if not payload.get("sub"):
            raise jwt.InvalidTokenError("JWT has no subject")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
