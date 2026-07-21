"""Authenticated CRUD for the structured Life Profile."""

import logging
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.db.client import get_db
from app.models.identity import IdentityProfileReadResponse, IdentityProfileResponse, IdentityProfileUpdate
from app.services.identity_service import IdentityService


router = APIRouter(prefix="/identity", tags=["identity"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


async def _can_access_identity(conn: asyncpg.Connection, caller_id: str, owner_id: str) -> bool:
    return bool(await conn.fetchval(
        """SELECT $1::uuid = $2::uuid OR EXISTS (
               SELECT 1 FROM public.memory_permissions permissions
               JOIN public.group_members membership ON membership.group_id = permissions.group_id
               WHERE permissions.memory_owner_id = $2::uuid AND membership.user_id = $1::uuid
           )""",
        caller_id, owner_id,
    ))


@router.get("", response_model=IdentityProfileReadResponse)
async def get_my_identity(
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    try:
        profile, exists = await IdentityService().get_or_create_owner_profile(
            conn, str(user["sub"]), user.get("email"),
        )
        return {"profile": profile, "exists": exists}
    except asyncpg.PostgresError as error:
        logger.exception("GET /identity failed")
        raise HTTPException(status_code=503, detail="Life Profile is temporarily unavailable") from error
    except Exception as error:
        logger.exception("GET /identity failed")
        raise HTTPException(status_code=500, detail="Life Profile could not be loaded") from error


@router.put("", response_model=IdentityProfileResponse)
async def update_my_identity(
    payload: IdentityProfileUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    try:
        # Keep native ``date`` objects for asyncpg while JSON columns are
        # serialised deliberately inside IdentityService.
        changes = payload.model_dump(exclude_unset=True)
        return await IdentityService().update_owner_profile(conn, str(user["sub"]), changes, user.get("email"))
    except asyncpg.PostgresError as error:
        logger.exception("Failed to save Life Profile for authenticated user")
        raise HTTPException(status_code=503, detail="Life Profile could not be saved") from error
    except Exception as error:
        logger.exception("Unexpected Life Profile save failure for authenticated user")
        raise HTTPException(status_code=500, detail="Life Profile could not be saved") from error


@router.get("/{owner_id}", response_model=IdentityProfileResponse)
async def get_shared_identity(
    owner_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    caller_id = str(user["sub"])
    try:
        allowed = await _can_access_identity(conn, caller_id, str(owner_id))
        if not allowed:
            raise HTTPException(status_code=403, detail="You do not have access to this Life Profile")
        return await IdentityService().load_for_access(conn, str(owner_id), is_owner=caller_id == str(owner_id))
    except HTTPException:
        raise
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load a shared Life Profile")
        raise HTTPException(status_code=503, detail="Life Profile is temporarily unavailable") from error
    except Exception as error:
        logger.exception("Unexpected shared Life Profile load failure")
        raise HTTPException(status_code=500, detail="Life Profile could not be loaded") from error
