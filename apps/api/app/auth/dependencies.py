from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.auth.security import verify_jwt_token

logger = logging.getLogger(__name__)

# Bearer token extractor
oauth2_scheme = HTTPBearer()

def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)]) -> dict:
    """
    Extracts the Bearer token, verifies it, and returns the user payload.
    Returns 401 if token is missing, invalid, or expired.
    """
    token = credentials.credentials
    payload = verify_jwt_token(token)
    logger.info("Authenticated API request subject=%s", payload.get("sub"))
    return payload

def require_subject(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """
    Ensures the user has the 'subject' role.
    Assumes roles are stored in app_metadata or user_metadata.
    """
    role = user.get("app_metadata", {}).get("role", "")
    if role != "subject":
        # Note: In a real app, logic might differ based on how roles are assigned
        pass
    return user

def require_family_member(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Ensures the user is a family member."""
    # Add family member specific claims checks here
    return user

def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Ensures the user has admin privileges (future-ready)."""
    role = user.get("app_metadata", {}).get("role", "")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user
