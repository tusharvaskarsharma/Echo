"""Opt-in integration checks.

Run `ECHO_RUN_INTEGRATION_TESTS=1 pytest` only with real Supabase/Pinecone
credentials.  The normal suite must stay hermetic and never mutate cloud data.
"""
import os
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("ECHO_RUN_INTEGRATION_TESTS") != "1",
    reason="requires explicitly configured Supabase and Pinecone services",
)


def test_database_url_is_configured():
    from app.config import get_settings
    assert get_settings().database_url
