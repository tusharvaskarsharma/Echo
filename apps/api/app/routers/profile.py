"""Authenticated profile settings and username availability endpoints."""

import json
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.client import get_db
from app.services.username_service import normalize_username, username_error


router = APIRouter(prefix="/profile", tags=["profile"])


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
    return _profile_response(row)
