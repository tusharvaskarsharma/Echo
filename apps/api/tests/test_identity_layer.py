"""Regression coverage for structured facts being kept out of semantic RAG."""

from datetime import date

from app.services.identity_service import (
    IdentityIntent, answer_identity_question, build_identity_context, classify_question, filter_shared_identity,
)


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
