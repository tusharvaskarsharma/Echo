"""Empty-account behaviour for Family Sharing and account privacy APIs."""

import asyncio
import json
from uuid import uuid4

from app.routers.groups import list_groups, list_invitations, shared_users
from app.routers.profile import PrivacyUpdate, get_privacy, update_privacy


class EmptyFamilyConnection:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def execute(self, query: str, *_args) -> None:
        self.queries.append(query)

    async def fetch(self, query: str, *_args) -> list[dict]:
        self.queries.append(query)
        return []


def test_new_account_family_endpoints_return_empty_collections() -> None:
    user = {"sub": "00000000-0000-0000-0000-000000000001"}
    conn = EmptyFamilyConnection()

    assert asyncio.run(list_groups(user, conn)) == []
    assert asyncio.run(list_invitations(user, conn)) == []
    assert asyncio.run(shared_users(user, conn)) == []

    shared_users_query = next(query for query in conn.queries if "SELECT member.user_id AS owner_id" in query)
    assert "ORDER BY owner.full_name NULLS LAST, owner.username NULLS LAST" in shared_users_query
    assert "member.user_id <> $1::uuid" in shared_users_query
    assert "BOOL_OR(permission.memory_owner_id IS NOT NULL) AS can_access" in shared_users_query


class SharedMemberConnection:
    async def fetch(self, _query: str, *_args) -> list[dict]:
        return [{
            "owner_id": uuid4(), "subject_id": None, "username": "alex",
            "full_name": "Alex Kumar", "can_access": False, "group_names": ["My Love"],
        }]


def test_shared_users_lists_accepted_members_without_granting_their_archive() -> None:
    user = {"sub": "00000000-0000-0000-0000-000000000001"}
    users = asyncio.run(shared_users(user, SharedMemberConnection()))

    assert users[0]["display_name"] == "Alex Kumar"
    assert users[0]["group_names"] == ["My Love"]
    assert users[0]["can_access"] is False


class PrivacyConnection:
    def __init__(self) -> None:
        self.preference_writes: list[dict[str, bool]] = []

    async def fetchrow(self, query: str, *_args) -> dict:
        assert "INSERT INTO public.profiles" in query
        assert "ON CONFLICT (id) DO UPDATE" in query
        preferences = json.loads(_args[2])
        self.preference_writes.append(preferences)
        return {"privacy_settings": preferences}


def test_privacy_endpoints_upsert_defaults_for_a_new_account() -> None:
    user = {"sub": "00000000-0000-0000-0000-000000000001", "email": "new@example.com"}
    conn = PrivacyConnection()

    assert asyncio.run(get_privacy(user, conn)) == {"share_data": False}
    assert asyncio.run(update_privacy(PrivacyUpdate(share_data=True), user, conn)) == {"share_data": True}
    assert conn.preference_writes == [{"share_data": False}, {"share_data": True}]
