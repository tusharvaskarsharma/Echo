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
    
    if settings.demo_mode:
        logger.warning("Demo mode active: bypassing JWT verification.")
        return {
            "sub": "00000000-0000-0000-0000-000000000000", 
            "role": "authenticated",
            "app_metadata": {"role": "subject"}
        }

    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="Supabase JWT secret not configured.")

    try:
        # Decode the token
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False} # Supabase aud can vary, usually 'authenticated'
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
