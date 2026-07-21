"""Regression coverage for structured facts being kept out of semantic RAG."""

import asyncio
from datetime import date

from app.services.identity_service import (
    IdentityIntent, IdentityService, answer_identity_question, build_identity_context, classify_question, filter_shared_identity,
)
from app.routers.identity import get_my_identity


def _profile():
    return {
        "user_id": "owner-1", "full_name": "Arun Kumar", "preferred_name": "Arun",
        "date_of_birth": date(1950, 5, 10), "occupation": "Railway workshop supervisor",
        "spouse": "Neha", "children": ["Maya", "Rohan"], "languages": ["Hindi", "English"],
        "email": "private@example.test", "medical_notes": "Private", "privacy_settings": {
            "shared_fields": ["full_name", "preferred_name", "occupation", "spouse", "children", "languages"],
        },
    }


def test_classifier_routes_structured_story_and_hybrid_questions():
    assert classify_question("What is your name?") == IdentityIntent.IDENTITY
    assert classify_question("How did you meet your wife?") == IdentityIntent.MIXED
    assert classify_question("What was your happiest memory?") == IdentityIntent.MEMORY
    assert classify_question("Tell me something") == IdentityIntent.GENERAL


def test_identity_answers_do_not_need_memories():
    profile = _profile()
    assert answer_identity_question("What is your occupation?", profile) == "Their occupation is Railway workshop supervisor."
    assert answer_identity_question("Who is your wife?", profile) == "Their spouse is Neha."
    assert answer_identity_question("How old are you?", profile).startswith("They are ")


def test_group_member_receives_only_selected_identity_fields():
    shared = filter_shared_identity(_profile(), is_owner=False)
    assert shared["full_name"] == "Arun Kumar"
    assert shared["spouse"] == "Neha"
    assert shared["email"] is None
    assert shared["medical_notes"] is None
    assert "private@example.test" not in build_identity_context(shared)


class _IdentityConnection:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def fetchrow(self, query: str, *_args):
        self.queries.append(query)
        if query.lstrip().startswith("SELECT"):
            return None
        if query.lstrip().startswith("INSERT"):
            return {
                "user_id": "owner-1",
                "full_name": None,
                "email": "owner@example.test",
                "languages": [],
                "children": [],
                "parents": [],
                "siblings": [],
                "grandchildren": [],
                "pets": [],
                "values": [],
                "social_links": {},
                "privacy_settings": {"shared_fields": []},
            }
        raise AssertionError(f"Unexpected query: {query}")


def test_new_life_profile_does_not_depend_on_the_legacy_profiles_table():
    connection = _IdentityConnection()
    profile = asyncio.run(IdentityService().ensure_owner_profile(connection, "owner-1", "owner@example.test"))

    assert profile["user_id"] == "owner-1"
    assert profile["email"] == "owner@example.test"
    assert all("public.profiles" not in query for query in connection.queries)


def test_missing_life_profile_creates_a_default_profile_instead_of_failing():
    connection = _IdentityConnection()
    profile, existed = asyncio.run(IdentityService().get_or_create_owner_profile(connection, "owner-1", "owner@example.test"))

    assert existed is False
    assert profile["user_id"] == "owner-1"
    assert profile["languages"] == []
    assert "ON CONFLICT (user_id) DO UPDATE" in connection.queries[-1]


def test_get_identity_returns_200_shape_for_a_brand_new_user():
    response = asyncio.run(get_my_identity({"sub": "owner-1", "email": "owner@example.test"}, _IdentityConnection()))

    assert response["exists"] is False
    assert response["profile"]["user_id"] == "owner-1"
