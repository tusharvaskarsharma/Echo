import httpx
import logging
from fastapi import HTTPException
from app.config import get_settings

logger = logging.getLogger(__name__)

class RealtimeService:
    def __init__(self):
        self.settings = get_settings()

    async def create_ephemeral_token(self) -> dict:
        """
        Calls the OpenAI REST API to generate a temporary client token for Realtime sessions.
        The token is bound to a specific configuration (VAD, voice, functions).
        """
        if not self.settings.openai_api_key:
            if self.settings.demo_mode:
                return {"client_secret": "demo_token_12345", "expires_at": 1999999999}
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        url = "https://api.openai.com/v1/realtime/sessions"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Configure the ephemeral session capabilities
        payload = {
            "model": self.settings.openai_realtime_model,
            "modalities": ["audio", "text"],
            "instructions": "You are Echo, a thoughtful interviewer helping to capture the life story of the user. Ask engaging questions and be an empathetic listener.",
            "voice": "alloy",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 200
            },
            "tools": [] # Functions for memory extraction will go here in the future
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # We only return the client secret (the ephemeral token) to the frontend
                client_secret = data.get("client_secret", {})
                if not client_secret:
                    logger.error("OpenAI response did not contain client_secret")
                    raise HTTPException(status_code=500, detail="Failed to generate realtime session token")
                    
                return {
                    "client_secret": client_secret.get("value"),
                    "expires_at": client_secret.get("expires_at")
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API Error: {e.response.status_code} {e.response.text}")
            raise HTTPException(status_code=502, detail="Failed to communicate with OpenAI API")
        except httpx.RequestError as e:
            logger.error(f"Network error calling OpenAI API: {e}")
            raise HTTPException(status_code=502, detail="Network error calling OpenAI API")
