import base64
from openai import AsyncOpenAI
from app.config import get_settings

class TTSService:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def generate_speech(self, text: str, voice: str = "alloy") -> str:
        """
        Generates speech using OpenAI TTS and returns base64 encoded MP3 audio.
        """
        response = await self.client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=text,
            response_format="mp3"
        )
        
        audio_data = response.content
        return base64.b64encode(audio_data).decode("utf-8")
