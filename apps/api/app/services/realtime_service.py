"""Gemini Live ephemeral-token provisioning for browser voice sessions."""

import datetime
import logging

import httpx
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiLiveService:
    def __init__(self):
        self.settings = get_settings()

    @staticmethod
    def _interviewer_setup(model: str) -> dict:
        """Return the provider setup locked into each short-lived credential."""
        return {
            "model": f"models/{model}",
            "generationConfig": {"responseModalities": ["AUDIO"]},
            "inputAudioTranscription": {},
            "outputAudioTranscription": {},
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "You are Echo, a thoughtful interviewer helping capture the user's life story. "
                        "Ask one empathetic, concise follow-up at a time. When the user shares a "
                        "meaningful life memory, call tag_memory with a short factual summary and topics. "
                        "Never invent a memory or tag a detail the user did not share."
                    )
                }]
            },
            "tools": [{
                "functionDeclarations": [{
                    "name": "tag_memory",
                    "description": "Mark a meaningful, user-shared life memory for review in the interview UI.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "summary": {"type": "STRING", "description": "A short factual summary of the memory."},
                            "topics": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Up to three relevant topics."}
                        },
                        "required": ["summary"]
                    }
                }]
            }]
        }

    async def create_ephemeral_token(self, user_id: str, session_id: str) -> dict:
        """Provision a constrained, one-use Gemini Live token for a browser session."""
        if not self.settings.gemini_api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=30)
        new_session_expires_at = now + datetime.timedelta(minutes=1)
        # AuthTokenService.CreateToken is currently a v1alpha endpoint. Keep
        # its wire format here instead of putting a Google SDK in the request
        # path; this API only needs a single, well-defined POST.
        request_body = {
            "uses": 1,
            "expireTime": expires_at.isoformat().replace("+00:00", "Z"),
            "newSessionExpireTime": new_session_expires_at.isoformat().replace("+00:00", "Z"),
            "bidiGenerateContentSetup": self._interviewer_setup(self.settings.gemini_live_model),
        }
        try:
            logger.info("Provisioning Gemini Live token for user %s", user_id)
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://generativelanguage.googleapis.com/v1alpha/auth_tokens",
                    headers={"x-goog-api-key": self.settings.gemini_api_key},
                    json=request_body,
                )
            if response.is_error:
                logger.error("Gemini Live token provisioning failed: status=%s body=%s", response.status_code, response.text[:500])
                raise HTTPException(status_code=502, detail="Gemini rejected Live token provisioning")
            token = response.json()
            access_token = token.get("name")
            if not access_token:
                raise HTTPException(status_code=502, detail="Gemini did not return a Live session token")
            logger.info("Provisioned Gemini Live token for user %s", user_id)
            return {
                "access_token": access_token,
                "model": self.settings.gemini_live_model,
                "session_id": session_id,
                "expires_at": token.get("expireTime") or expires_at.isoformat(),
                "setup": self._interviewer_setup(self.settings.gemini_live_model),
            }
        except HTTPException:
            raise
        except Exception as error:
            logger.exception("Gemini Live token provisioning failed for user %s", user_id)
            raise HTTPException(status_code=502, detail="Failed to provision a Gemini Live session") from error
