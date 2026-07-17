"""Offline tests for the authentication and tenant-bound repository contract."""
import asyncio
from uuid import uuid4

import jwt
import pytest

from app.auth.security import verify_jwt_token
from app.config import get_settings
from app.db import repositories


def test_supabase_jwt_requires_expected_issuer_audience_and_subject(monkeypatch):
    settings = get_settings()
    secret = "test-secret-with-at-least-thirty-two-bytes"
    monkeypatch.setattr(settings, "supabase_jwt_secret", secret)
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    payload = {"sub": str(uuid4()), "aud": "authenticated", "iss": "https://example.supabase.co/auth/v1"}
    token = jwt.encode(payload, secret, algorithm="HS256")
    assert verify_jwt_token(token)["sub"] == payload["sub"]

    wrong_audience = jwt.encode({**payload, "aud": "anon"}, secret, algorithm="HS256")
    with pytest.raises(Exception):
        verify_jwt_token(wrong_audience)


class FakeConnection:
    def __init__(self): self.calls = []
    async def fetchrow(self, query, *args): self.calls.append((query, args)); return None


def test_session_lookup_is_scoped_to_owner():
    conn = FakeConnection()
    asyncio.run(repositories.get_session(conn, "session-a", "user-a"))
    query, args = conn.calls[0]
    assert "user_id = $2" in query and args == ("session-a", "user-a")
