"""Small Groq REST client used by Echo's text, JSON, and transcription paths."""

import json
import logging
from pathlib import Path
from typing import AsyncIterator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqUnavailableError(RuntimeError):
    """A transient provider failure: timeout, rate limit, or 5xx response."""


class GroqConfigurationError(RuntimeError):
    """A local credential/model/request configuration problem."""


class GroqService:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {"Authorization": f"Bearer {self.settings.groq_api_key}"}

    def _require_api_key(self) -> None:
        if not self.settings.groq_api_key:
            raise GroqConfigurationError("GROQ_API_KEY is not configured")

    @staticmethod
    def _classify_http_error(error: httpx.HTTPStatusError) -> RuntimeError:
        status = error.response.status_code
        # Do not log prompts or headers: both can contain private memories or
        # credentials. The provider's status/body are enough for diagnosis.
        logger.error("Groq request failed with HTTP %s: %s", status, error.response.text[:500])
        if status in {408, 429} or status >= 500:
            return GroqUnavailableError(f"Groq returned HTTP {status}")
        return GroqConfigurationError(f"Groq rejected the request with HTTP {status}")

    async def complete(self, messages: list[dict], *, json_mode: bool = False) -> str:
        self._require_api_key()
        payload: dict = {
            "model": self.settings.groq_persona_model,
            "messages": messages,
            "temperature": 0.3,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        logger.info("Calling Groq completion model=%s json_mode=%s messages=%d", payload["model"], json_mode, len(messages))
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{GROQ_API_BASE}/chat/completions", headers={**self.headers, "Content-Type": "application/json"}, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise self._classify_http_error(error) from error
        except httpx.RequestError as error:
            logger.exception("Groq completion request failed")
            raise GroqUnavailableError("Groq completion request could not be completed") from error
        try:
            return response.json()["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as error:
            logger.exception("Groq completion response had an unexpected shape")
            raise GroqUnavailableError("Groq returned an invalid completion response") from error

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        self._require_api_key()
        payload = {
            "model": self.settings.groq_persona_model,
            "messages": messages,
            "temperature": 0.3,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", f"{GROQ_API_BASE}/chat/completions", headers={**self.headers, "Content-Type": "application/json"}, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    value = line[6:]
                    if value == "[DONE]":
                        return
                    try:
                        content = json.loads(value)["choices"][0]["delta"].get("content")
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if content:
                        yield content

    async def transcribe(self, file_path: str) -> list[dict]:
        self._require_api_key()
        path = Path(file_path)
        with path.open("rb") as audio_file:
            files = {"file": (path.name, audio_file, "application/octet-stream")}
            data = {"model": "whisper-large-v3-turbo", "response_format": "verbose_json", "timestamp_granularities[]": "segment"}
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{GROQ_API_BASE}/audio/transcriptions", headers=self.headers, data=data, files=files)
                response.raise_for_status()
        return response.json().get("segments", [])
