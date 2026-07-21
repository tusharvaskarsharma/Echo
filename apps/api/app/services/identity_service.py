"""Structured identity source used before semantic memory retrieval."""

from __future__ import annotations

import json
import re
from datetime import date
from enum import StrEnum
from typing import Any

import asyncpg

from app.models.identity import IDENTITY_FIELDS, JSON_FIELDS, LIST_FIELDS


class IdentityIntent(StrEnum):
    IDENTITY = "identity"
    MEMORY = "memory"
    MIXED = "mixed"
    GENERAL = "general"


_MEMORY_SIGNALS = {
    "memory", "remember", "story", "happiest", "regret", "proudest", "lesson", "advice",
    "childhood", "how did", "when did", "what happened", "first job", "think", "feel", "felt",
    "experience", "meet", "met", "learn from life",
}
_IDENTITY_SIGNALS = {
    "your name", "called", "age", "old are", "birthday", "born", "occupation", "profession",
    "what do you do", "job", "career", "where are you from", "hometown", "live", "city", "language",
    "nationality", "religion", "pronouns", "gender", "wife", "spouse", "husband", "children",
    "parents", "siblings", "grandchildren", "pets", "education", "studied", "who are you", "about yourself",
    "favorite", "favourite", "motto", "quote", "values", "blood group", "allerg", "website", "email",
}


def classify_question(question: str) -> IdentityIntent:
    """Deterministically route stable-fact questions before invoking RAG."""
    normalized = re.sub(r"\s+", " ", question.lower()).strip()
    def has_signal(signal: str) -> bool:
        return signal in normalized if " " in signal else bool(re.search(rf"\b{re.escape(signal)}\b", normalized))

    identity = any(has_signal(signal) for signal in _IDENTITY_SIGNALS)
    memory = any(has_signal(signal) for signal in _MEMORY_SIGNALS)
    if identity and memory:
        return IdentityIntent.MIXED
    if identity:
        return IdentityIntent.IDENTITY
    if memory:
        return IdentityIntent.MEMORY
    return IdentityIntent.GENERAL


def _row_to_profile(row: asyncpg.Record | dict[str, Any] | None, *, fallback_user_id: str, fallback_name: str | None = None) -> dict[str, Any]:
    profile: dict[str, Any] = dict(row) if row else {"user_id": fallback_user_id}
    profile.setdefault("user_id", fallback_user_id)
    if not profile.get("full_name") and fallback_name and fallback_name != "Your legacy":
        profile["full_name"] = fallback_name
    for field in JSON_FIELDS:
        value = profile.get(field)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = None
        if field in LIST_FIELDS:
            profile[field] = value if isinstance(value, list) else []
        elif field == "social_links":
            profile[field] = value if isinstance(value, dict) else {}
        else:
            profile[field] = value if isinstance(value, dict) else {"shared_fields": []}
    for field in IDENTITY_FIELDS:
        profile.setdefault(field, [] if field in LIST_FIELDS else {} if field == "social_links" else None)
    return profile


def filter_shared_identity(profile: dict[str, Any], *, is_owner: bool) -> dict[str, Any]:
    """Apply the profile owner's field allow-list for an accepted group member."""
    if is_owner:
        return profile
    allowed = set(profile.get("privacy_settings", {}).get("shared_fields", []))
    result: dict[str, Any] = {"user_id": profile["user_id"]}
    for field in allowed & IDENTITY_FIELDS:
        result[field] = profile.get(field)
    return _row_to_profile(result, fallback_user_id=str(profile["user_id"]))


def _nonempty(value: Any) -> bool:
    return bool(value) if isinstance(value, (str, list, dict)) else value is not None


_FIELD_LABELS = {
    "full_name": "Full name", "preferred_name": "Preferred name", "date_of_birth": "Date of birth",
    "gender": "Gender", "pronouns": "Pronouns", "occupation": "Occupation", "education": "Education",
    "nationality": "Nationality", "religion": "Religion", "languages": "Languages", "hometown": "Hometown",
    "current_city": "Current city", "biography": "Biography", "spouse": "Spouse", "children": "Children",
    "parents": "Parents", "siblings": "Siblings", "grandchildren": "Grandchildren", "pets": "Pets",
    "website": "Website", "social_links": "Social links", "email": "Email", "values": "Values",
    "motto": "Motto", "favorite_quote": "Favorite quote", "favorite_song": "Favorite song",
    "favorite_book": "Favorite book", "favorite_food": "Favorite food", "favorite_place": "Favorite place",
    "blood_group": "Blood group", "allergies": "Allergies", "medical_notes": "Medical notes",
}


def build_identity_context(profile: dict[str, Any]) -> str:
    """Format only populated, authorised stable facts for the persona prompt."""
    lines: list[str] = []
    for field in sorted(IDENTITY_FIELDS):
        value = profile.get(field)
        if not _nonempty(value):
            continue
        if field == "date_of_birth" and isinstance(value, date):
            value = value.isoformat()
        elif isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            value = ", ".join(f"{key}: {link}" for key, link in value.items())
        lines.append(f"- {_FIELD_LABELS[field]}: {value}")
    return "\n".join(lines) or "No Life Profile facts have been saved yet."


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _answer_for_field(profile: dict[str, Any], field: str, *, prefix: str = "") -> str | None:
    value = profile.get(field)
    if not _nonempty(value):
        return None
    if field == "date_of_birth":
        rendered = f"{value.strftime('%B')} {value.day}, {value.year}" if hasattr(value, "strftime") else value
        return f"{prefix}{rendered}."
    if isinstance(value, list):
        return f"{prefix}{', '.join(str(item) for item in value)}."
    return f"{prefix}{value}."


def answer_identity_question(question: str, profile: dict[str, Any]) -> str | None:
    """Answer narrow identity questions without calling the LLM or vector search."""
    q = re.sub(r"\s+", " ", question.lower()).strip()
    if "wife" in q or "spouse" in q or "husband" in q:
        return _answer_for_field(profile, "spouse", prefix="Their spouse is ")
    if "children" in q or "child" in q:
        children = profile.get("children") or []
        if children:
            return f"They have {len(children)} child{'ren' if len(children) != 1 else ''}: {', '.join(children)}."
        return None
    if "grandchild" in q:
        return _answer_for_field(profile, "grandchildren", prefix="Their grandchildren are ")
    if "sibling" in q:
        return _answer_for_field(profile, "siblings", prefix="Their siblings are ")
    if "parent" in q or "mother" in q or "father" in q:
        return _answer_for_field(profile, "parents", prefix="Their parents are ")
    if "pet" in q:
        return _answer_for_field(profile, "pets", prefix="Their pets are ")
    if "how old" in q or re.search(r"\bage\b", q):
        dob = profile.get("date_of_birth")
        if isinstance(dob, date):
            return f"They are {_age(dob)} years old."
        return None
    if "birthday" in q or "date of birth" in q:
        return _answer_for_field(profile, "date_of_birth", prefix="Their birthday is ")
    if "born" in q or "hometown" in q or "where are you from" in q:
        return _answer_for_field(profile, "hometown", prefix="They are from ")
    if "live" in q or "current city" in q:
        return _answer_for_field(profile, "current_city", prefix="They live in ")
    if "language" in q:
        return _answer_for_field(profile, "languages", prefix="They speak ")
    if "occupation" in q or "profession" in q or "what do you do" in q or "career" in q or "job" in q:
        return _answer_for_field(profile, "occupation", prefix="Their occupation is ")
    if "education" in q or "stud" in q:
        return _answer_for_field(profile, "education", prefix="Their education is ")
    if "nationality" in q:
        return _answer_for_field(profile, "nationality", prefix="Their nationality is ")
    if "religion" in q:
        return _answer_for_field(profile, "religion", prefix="Their religion is ")
    if "pronoun" in q:
        return _answer_for_field(profile, "pronouns", prefix="Their pronouns are ")
    if "gender" in q:
        return _answer_for_field(profile, "gender", prefix="Their gender is ")
    if "favorite song" in q or "favourite song" in q:
        return _answer_for_field(profile, "favorite_song", prefix="Their favorite song is ")
    if "favorite book" in q or "favourite book" in q:
        return _answer_for_field(profile, "favorite_book", prefix="Their favorite book is ")
    if "favorite food" in q or "favourite food" in q:
        return _answer_for_field(profile, "favorite_food", prefix="Their favorite food is ")
    if "favorite place" in q or "favourite place" in q:
        return _answer_for_field(profile, "favorite_place", prefix="Their favorite place is ")
    if "motto" in q:
        return _answer_for_field(profile, "motto", prefix="Their motto is ")
    if "favorite quote" in q or "favourite quote" in q:
        return _answer_for_field(profile, "favorite_quote", prefix="Their favorite quote is ")
    if "values" in q:
        return _answer_for_field(profile, "values", prefix="Their values include ")
    if "called" in q or "preferred name" in q:
        return _answer_for_field(profile, "preferred_name", prefix="People call them ") or _answer_for_field(profile, "full_name", prefix="Their name is ")
    if "name" in q:
        return _answer_for_field(profile, "full_name", prefix="Their name is ") or _answer_for_field(profile, "preferred_name", prefix="They go by ")
    if "who are you" in q or "about yourself" in q:
        details = [
            profile.get("preferred_name") or profile.get("full_name"), profile.get("occupation"),
            profile.get("current_city") or profile.get("hometown"), profile.get("biography"),
        ]
        details = [str(detail) for detail in details if _nonempty(detail)]
        return " ".join(details) if details else None
    return None


class IdentityService:
    async def ensure_owner_profile(self, conn: asyncpg.Connection, user_id: str, email: str | None = None) -> dict[str, Any]:
        """Create a sparse owner row, seeding known account details once."""
        row = await conn.fetchrow(
            """INSERT INTO public.identity_profiles (user_id, full_name, email)
               VALUES ($1, (SELECT full_name FROM public.profiles WHERE id = $1), $2)
               ON CONFLICT (user_id) DO NOTHING
               RETURNING *""",
            user_id, email,
        )
        if not row:
            row = await conn.fetchrow("SELECT * FROM public.identity_profiles WHERE user_id = $1", user_id)
        return _row_to_profile(row, fallback_user_id=user_id)

    async def load_for_access(
        self, conn: asyncpg.Connection, owner_id: str, *, is_owner: bool, fallback_name: str | None = None,
    ) -> dict[str, Any]:
        row = await conn.fetchrow("SELECT * FROM public.identity_profiles WHERE user_id = $1", owner_id)
        profile = _row_to_profile(row, fallback_user_id=owner_id, fallback_name=fallback_name)
        return filter_shared_identity(profile, is_owner=is_owner)

    async def update_owner_profile(self, conn: asyncpg.Connection, user_id: str, changes: dict[str, Any], email: str | None = None) -> dict[str, Any]:
        await self.ensure_owner_profile(conn, user_id, email)
        if not changes:
            return await self.ensure_owner_profile(conn, user_id, email)
        assignments: list[str] = []
        values: list[Any] = []
        for field, value in changes.items():
            if field not in IDENTITY_FIELDS and field != "privacy_settings":
                continue
            values.append(json.dumps(value) if field in JSON_FIELDS and value is not None else value)
            placeholder = f"${len(values)}"
            assignments.append(f"{field} = {placeholder}::jsonb" if field in JSON_FIELDS else f"{field} = {placeholder}")
        if not assignments:
            return await self.ensure_owner_profile(conn, user_id, email)
        values.append(user_id)
        row = await conn.fetchrow(
            f"UPDATE public.identity_profiles SET {', '.join(assignments)}, updated_at = now() WHERE user_id = ${len(values)} RETURNING *",
            *values,
        )
        return _row_to_profile(row, fallback_user_id=user_id)
