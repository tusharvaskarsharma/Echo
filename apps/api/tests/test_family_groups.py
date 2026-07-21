"""Focused authorization checks for private Family Group sharing."""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.routers.echo_conversation import _resolve_access
from app.routers.groups import _can_access_owner, _require_group_owner


class GroupAccessConnection:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def fetchval(self, _query: str, _caller_id: str, _owner_id: str) -> bool:
        return self.allowed


def test_shared_memories_require_a_database_membership_grant() -> None:
    assert asyncio.run(_can_access_owner(GroupAccessConnection(True), "member", "owner"))
    assert not asyncio.run(_can_access_owner(GroupAccessConnection(False), "member", "owner"))


class OwnershipConnection:
    async def fetchrow(self, _query: str, group_id: str, _user_id: str) -> dict:
        return {"id": group_id, "owner_id": "owner", "role": "member"}


def test_only_group_owner_can_change_membership_or_sharing() -> None:
    owner = asyncio.run(_require_group_owner(OwnershipConnection(), "group", "owner"))
    assert owner["owner_id"] == "owner"
    with pytest.raises(HTTPException) as error:
        asyncio.run(_require_group_owner(OwnershipConnection(), "group", "member"))
    assert error.value.status_code == 403


class EchoAccessConnection:
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


def test_echo_derives_the_selected_owner_and_requires_group_access() -> None:
    result = asyncio.run(_resolve_access(EchoAccessConnection(True), "member", "owner"))
    assert result == ("subject-owner", "Grandma", "group", "owner")
    with pytest.raises(HTTPException) as error:
        asyncio.run(_resolve_access(EchoAccessConnection(False), "member", "owner"))
    assert error.value.status_code == 403


def test_family_group_migration_defines_foreign_keys_indexes_and_rls() -> None:
    migration = Path("app/db/migrations/020_family_groups.sql").read_text(encoding="utf-8")
    for table in ("public.groups", "public.group_members", "public.memory_permissions"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in migration
    assert "REFERENCES auth.users(id) ON DELETE CASCADE" in migration
    assert "UNIQUE (group_id, user_id)" in migration
    assert "idx_group_members_user_id" in migration
    assert "group_members_can_read_shared_memories" in migration
    assert "current_user_is_group_member" in migration
