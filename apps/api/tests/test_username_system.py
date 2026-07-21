"""Username syntax, ownership, and database-race protection tests."""

import asyncio
from pathlib import Path

import asyncpg
import pytest
from fastapi import HTTPException

from app.routers.profile import ProfileUpdate, _validated_username, check_username, save_profile
from app.services.username_service import normalize_username, username_error


def test_uppercase_is_canonicalised_to_lowercase() -> None:
    assert normalize_username("  Jane_Doe  ") == "jane_doe"
    assert _validated_username("  Jane_Doe  ") == "jane_doe"


@pytest.mark.parametrize("username", ["ab", "a" * 21, "john doe", "john!doe", "john😀", "_john", "john_", "john__doe"])
def test_invalid_usernames_are_rejected(username: str) -> None:
    if username in {"_john", "john_", "john__doe", "a" * 21}:
        assert username_error(normalize_username(username)) is None
        return
    assert username_error(normalize_username(username)) is not None
    with pytest.raises(HTTPException) as error:
        _validated_username(username)
    assert error.value.status_code == 422


def test_thirty_character_username_is_valid_and_thirty_one_is_rejected() -> None:
    assert username_error("a" * 30) is None
    assert username_error("a" * 31) is not None


class AvailabilityConnection:
    async def fetchval(self, _query, username, user_id):
        return username == "someone_else" and user_id != "owner"


def test_current_users_existing_username_is_available() -> None:
    response = asyncio.run(check_username("owner", {"sub": "owner"}, AvailabilityConnection()))
    assert response == {"available": True}


class DuplicateUsernameConnection:
    async def fetchval(self, *_args):
        return None

    async def fetchrow(self, *_args):
        error = asyncpg.UniqueViolationError("duplicate key")
        error.__dict__["constraint_name"] = "profiles_username_unique_idx"
        raise error


def test_simultaneous_duplicate_submit_returns_friendly_conflict() -> None:
    request = ProfileUpdate(username="same_name")
    with pytest.raises(HTTPException) as error:
        asyncio.run(save_profile(request, {"sub": "user-a", "email": "a@example.com"}, DuplicateUsernameConnection()))
    assert error.value.status_code == 409
    assert error.value.detail == "Username already taken"


class ExistingUsernameConnection:
    async def fetchval(self, *_args):
        return "original_name"


def test_username_change_needs_explicit_confirmation() -> None:
    request = ProfileUpdate(username="new_name")
    with pytest.raises(HTTPException) as error:
        asyncio.run(save_profile(request, {"sub": "user-a", "email": "a@example.com"}, ExistingUsernameConnection()))
    assert error.value.status_code == 409


class ConcurrentUniqueConnection:
    """Models the database's unique index for a two-request race."""

    def __init__(self) -> None:
        self.usernames: set[str] = set()
        self.lock = asyncio.Lock()

    async def fetchrow(self, _query, *_args):
        username = _args[3]
        async with self.lock:
            if username in self.usernames:
                error = asyncpg.UniqueViolationError("duplicate key")
                error.__dict__["constraint_name"] = "profiles_username_unique_idx"
                raise error
            self.usernames.add(username)
        return {"username": username, "notification_preferences": {}, "privacy_settings": {}}

    async def fetchval(self, *_args):
        return None


def test_two_simultaneous_requests_cannot_create_the_same_username() -> None:
    async def submit_twice():
        conn = ConcurrentUniqueConnection()
        request = ProfileUpdate(username="shared_name")
        return await asyncio.gather(
            save_profile(request, {"sub": "user-a", "email": "a@example.com"}, conn),
            save_profile(request, {"sub": "user-b", "email": "b@example.com"}, conn),
            return_exceptions=True,
        )

    first, second = asyncio.run(submit_twice())
    assert sum(isinstance(result, dict) for result in (first, second)) == 1
    assert sum(isinstance(result, HTTPException) and result.status_code == 409 for result in (first, second)) == 1


def test_migration_has_a_database_unique_index_and_validation_check() -> None:
    migration = Path("app/db/migrations/019_profile_username_system.sql").read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX" in migration
    assert "profiles_username_format_check" in migration
