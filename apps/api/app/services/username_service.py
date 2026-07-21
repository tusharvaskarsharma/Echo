"""Canonical username handling shared by the profile API and its tests."""

import re


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
ALLOWED_USERNAME = re.compile(r"^[a-z0-9_]+$")


def normalize_username(value: str) -> str:
    """Return the canonical form persisted by the database."""
    return value.strip().lower()


def username_error(value: str) -> str | None:
    """Return the user-facing syntax error, or ``None`` for a valid username."""
    if not (USERNAME_MIN_LENGTH <= len(value) <= USERNAME_MAX_LENGTH):
        return "Username must be between 3 and 30 characters"
    if not ALLOWED_USERNAME.fullmatch(value):
        return "Only lowercase letters, numbers and underscore allowed"
    return None
