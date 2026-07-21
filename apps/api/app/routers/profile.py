"""Authenticated profile settings and username availability endpoints."""

import json
import logging
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.client import get_db
from app.services.username_service import normalize_username, username_error


router = APIRouter(prefix="/profile", tags=["profile"])
privacy_router = APIRouter(prefix="/privacy", tags=["privacy"])
logger = logging.getLogger(__name__)


class ProfileUpdate(BaseModel):
    username: str = Field(max_length=200)
    full_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2_000)
    timezone: str | None = Field(default="UTC", max_length=100)
    language: str | None = Field(default="en", max_length=35)
    country: str | None = Field(default=None, max_length=100)
    theme_preference: str | None = Field(default="system", max_length=30)
    notifications: bool = True
    share_data: bool = False
    # A username is an identity used in group invitations.  Existing users can
    # set it during onboarding; later changes require an intentional, explicit
    # confirmation from the client and are also enforced here server-side.
    confirm_username_change: bool = False


class PrivacyUpdate(BaseModel):
    """The durable, account-owned sharing preference stored on profiles."""

    share_data: bool


def _trim_or_none(value: str | None) -> str | None:
    return value.strip() or None if value else None


def _validated_username(raw_username: str) -> str:
    username = normalize_username(raw_username)
    error = username_error(username)
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)
    return username


def _profile_response(row: asyncpg.Record) -> dict:
    profile = dict(row)
    for field in ("notification_preferences", "privacy_settings"):
        if isinstance(profile.get(field), str):
            profile[field] = json.loads(profile[field])
    return profile


def _privacy_response(row: asyncpg.Record) -> dict[str, bool]:
    settings = row["privacy_settings"] or {}
    if isinstance(settings, str):
        settings = json.loads(settings)
    return {"share_data": bool(settings.get("share_data", False))}


async def _upsert_privacy_settings(
    conn: asyncpg.Connection, user: dict, settings: dict[str, bool] | None = None,
) -> asyncpg.Record:
    """Create a preference row for new users and safely merge later updates."""
    incoming = settings or {"share_data": False}
    return await conn.fetchrow(
        """INSERT INTO public.profiles (id, email, privacy_settings)
           VALUES ($1, $2, $3::jsonb)
           ON CONFLICT (id) DO UPDATE SET
             email = COALESCE(public.profiles.email, EXCLUDED.email),
             privacy_settings = COALESCE(public.profiles.privacy_settings, '{}'::jsonb) || EXCLUDED.privacy_settings,
             updated_at = now()
           RETURNING privacy_settings""",
        user["sub"], user.get("email"), json.dumps(incoming),
    )


@router.get("/summary")
async def get_dashboard_summary(
    current_user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict[str, int]:
    """Return the authenticated owner's completed-recording and memory totals."""
    try:
        row = await conn.fetchrow(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'completed')::int AS session_count,
              (SELECT COUNT(*)::int FROM public.memories WHERE user_id = $1) AS memory_count
            FROM public.sessions
            WHERE user_id = $1
            """,
            current_user["sub"],
        )
        return {
            "session_count": int(row["session_count"] or 0),
            "memory_count": int(row["memory_count"] or 0),
        }
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load dashboard summary for user %s", current_user["sub"])
        raise HTTPException(status_code=503, detail="Dashboard totals are temporarily unavailable") from error


@router.get("/check-username")
async def check_username(
    username: str = Query(..., max_length=200),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    conn: Annotated[asyncpg.Connection, Depends(get_db)] = None,
) -> dict[str, bool | str]:
    """Check a syntactically-valid username without exposing profile details."""
    canonical_username = _validated_username(username)
    taken = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM public.profiles WHERE username = $1 AND id <> $2)",
        canonical_username,
        current_user["sub"],
    )
    if taken:
        return {"available": False, "reason": "Username already taken"}
    return {"available": True}


@privacy_router.get("")
async def get_privacy(
    current_user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict[str, bool]:
    """Return default privacy preferences even before profile onboarding runs."""
    try:
        return _privacy_response(await _upsert_privacy_settings(conn, current_user))
    except asyncpg.PostgresError as error:
        logger.exception("Failed to load privacy settings for user %s", current_user["sub"])
        raise HTTPException(status_code=503, detail="Privacy settings are temporarily unavailable") from error


@privacy_router.patch("")
async def update_privacy(
    privacy: PrivacyUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict[str, bool]:
    """Upsert rather than assuming an existing consent/preferences row."""
    try:
        row = await _upsert_privacy_settings(conn, current_user, {"share_data": privacy.share_data})
        return _privacy_response(row)
    except asyncpg.PostgresError as error:
        logger.exception("Failed to save privacy settings for user %s", current_user["sub"])
        raise HTTPException(status_code=503, detail="Privacy settings could not be saved") from error


@router.put("")
async def save_profile(
    profile: ProfileUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
) -> dict:
    """Save the authenticated user's profile with database-enforced uniqueness."""
    username = _validated_username(profile.username)
    existing_username = await conn.fetchval(
        "SELECT username FROM public.profiles WHERE id = $1", current_user["sub"]
    )
    if existing_username and existing_username != username and not profile.confirm_username_change:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm your username change before saving it",
        )
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO public.profiles (
                id, email, full_name, username, bio, timezone, language, country,
                theme_preference, notification_preferences, privacy_settings
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                username = EXCLUDED.username,
                bio = EXCLUDED.bio,
                timezone = EXCLUDED.timezone,
                language = EXCLUDED.language,
                country = EXCLUDED.country,
                theme_preference = EXCLUDED.theme_preference,
                notification_preferences = EXCLUDED.notification_preferences,
                privacy_settings = EXCLUDED.privacy_settings
            RETURNING *
            """,
            current_user["sub"], current_user.get("email"), _trim_or_none(profile.full_name), username,
            _trim_or_none(profile.bio), _trim_or_none(profile.timezone) or "UTC",
            _trim_or_none(profile.language) or "en", _trim_or_none(profile.country),
            _trim_or_none(profile.theme_preference) or "system",
            json.dumps({"email": profile.notifications}), json.dumps({"share_data": profile.share_data}),
        )
    except asyncpg.UniqueViolationError as error:
        # The availability check is advisory; this is authoritative when two
        # users submit the same name at once.
        if error.constraint_name in {"profiles_username_key", "profiles_username_unique_idx"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken") from error
        raise
    except asyncpg.PostgresError as error:
        logger.exception("Failed to save profile for user %s", current_user["sub"])
        raise HTTPException(status_code=503, detail="Profile settings could not be saved") from error
    return _profile_response(row)
