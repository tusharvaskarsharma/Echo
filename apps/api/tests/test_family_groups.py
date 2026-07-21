"""Focused authorization checks for private Family Group sharing."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.routers.emmy_conversation import _resolve_access
from app.routers.groups import (
    InvitationCreate,
    _can_access_owner,
    _require_group_owner,
    _require_pending_invitation,
    direct_member_addition_is_disabled,
)


class GroupAccessConnection:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def fetchval(self, _query: str, _caller_id: str, _owner_id: str) -> bool:
        return self.allowed


def test_shared_memories_require_a_database_membership_grant() -> None:
    assert asyncio.run(_can_access_owner(GroupAccessConnection(True), "member", "owner"))
    assert not asyncio.run(_can_access_owner(GroupAccessConnection(False), "member", "owner"))


def test_invitation_state_must_be_pending_and_unexpired_before_acceptance() -> None:
    _require_pending_invitation({"status": "pending", "expires_at": datetime.now(timezone.utc) + timedelta(days=1)})
    with pytest.raises(HTTPException) as declined:
        _require_pending_invitation({"status": "declined", "expires_at": datetime.now(timezone.utc) + timedelta(days=1)})
    assert declined.value.status_code == 409
    with pytest.raises(HTTPException) as expired:
        _require_pending_invitation({"status": "pending", "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
    assert expired.value.status_code == 410


def test_legacy_member_endpoint_cannot_bypass_invitation_acceptance() -> None:
    with pytest.raises(HTTPException) as error:
        asyncio.run(direct_member_addition_is_disabled("group", InvitationCreate(username="member"), {"sub": "owner"}))
    assert error.value.status_code == 410


class OwnershipConnection:
    async def fetchrow(self, _query: str, group_id: str, _user_id: str) -> dict:
        return {"id": group_id, "owner_id": "owner", "role": "member"}


def test_only_group_owner_can_change_membership_or_sharing() -> None:
    owner = asyncio.run(_require_group_owner(OwnershipConnection(), "group", "owner"))
    assert owner["owner_id"] == "owner"
    with pytest.raises(HTTPException) as error:
        asyncio.run(_require_group_owner(OwnershipConnection(), "group", "member"))
    assert error.value.status_code == 403


class EmmyAccessConnection:
    def __init__(self, group_allowed: bool) -> None:
        self.group_allowed = group_allowed

    async def fetchrow(self, query: str, *_args):
        if "FROM subjects" in query:
            return {"id": "subject-owner", "user_id": "owner", "full_name": "Grandma"}
        if "FROM legacy_contacts" in query:
            return None
        raise AssertionError(query)

    async def fetchval(self, query: str, *_args):
        assert "memory_permissions" in query
        return self.group_allowed


def test_emmy_derives_the_selected_owner_and_requires_group_access() -> None:
    result = asyncio.run(_resolve_access(EmmyAccessConnection(True), "member", "owner"))
    assert result == ("subject-owner", "Grandma", "group", "owner")
    with pytest.raises(HTTPException) as error:
        asyncio.run(_resolve_access(EmmyAccessConnection(False), "member", "owner"))
    assert error.value.status_code == 403


def test_family_group_migration_defines_foreign_keys_indexes_and_rls() -> None:
    migration = Path("app/db/migrations/020_family_groups.sql").read_text(encoding="utf-8")
    for table in ("public.groups", "public.group_members", "public.memory_permissions"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in migration
    assert "REFERENCES auth.users(id) ON DELETE CASCADE" in migration
    assert "UNIQUE (group_id, user_id)" in migration
    assert "idx_group_members_user_id" in migration
    assert "group_members_can_read_shared_memories" in migration
    assert "private.current_user_is_group_member" in migration


def test_invitation_migration_requires_acceptance_and_expiration_controls() -> None:
    migration = Path("app/db/migrations/021_group_invitations.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.group_invitations" in migration
    assert "('pending', 'accepted', 'declined', 'expired')" in migration
    assert "group_invitations_one_pending_per_user" in migration
    assert "expires_at TIMESTAMPTZ" in migration
    assert "recipient_can_respond_to_pending_invitation" in migration
    assert "invitation_acceptance_creates_membership" in migration
    assert (
        "DROP POLICY IF EXISTS invitation_acceptance_creates_membership ON public.group_members;"
        in migration
    )
