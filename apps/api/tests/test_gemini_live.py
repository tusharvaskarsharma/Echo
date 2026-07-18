"""Offline contract tests for Gemini Live token provisioning."""

import asyncio

from app.services.realtime_service import GeminiLiveService
import app.services.realtime_service as realtime_module


class FakeResponse:
    is_error = False

    def json(self):
        return {"name": "ephemeral-token", "expireTime": "2026-07-18T01:00:00Z"}


class FakeClient:
    request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, url, *, headers, json):
        self.request = {"url": url, "headers": headers, "json": json}
        return FakeResponse()


def test_gemini_live_token_request_uses_constrained_v1alpha_contract(monkeypatch):
    settings = GeminiLiveService().settings
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    monkeypatch.setattr(settings, "gemini_live_model", "gemini-3.1-flash-live-preview")
    fake_client = FakeClient()
    monkeypatch.setattr(realtime_module.httpx, "AsyncClient", lambda **_kwargs: fake_client)

    token = asyncio.run(GeminiLiveService().create_ephemeral_token("user-123", "session-123"))

    assert token["access_token"] == "ephemeral-token"
    assert token["session_id"] == "session-123"
    assert token["setup"]["tools"][0]["functionDeclarations"][0]["name"] == "tag_memory"
    request = fake_client.request
    assert request["url"].endswith("/v1alpha/auth_tokens")
    assert request["headers"]["x-goog-api-key"] == "test-gemini-key"
    token_config = request["json"]
    assert token_config["uses"] == 1
    assert token_config["bidiGenerateContentSetup"]["model"] == "models/gemini-3.1-flash-live-preview"
    assert token_config["bidiGenerateContentSetup"]["generationConfig"]["responseModalities"] == ["AUDIO"]
    assert token_config["bidiGenerateContentSetup"]["tools"][0]["functionDeclarations"][0]["name"] == "tag_memory"
