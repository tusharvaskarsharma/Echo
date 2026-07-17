import httpx
import tempfile

from app.services.groq_service import GroqService


class TranscriptionService:
    def __init__(self):
        self.groq = GroqService()

    async def download_audio(self, audio_url: str) -> str:
        if not audio_url:
            raise ValueError("No valid audio URL provided for transcription.")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=30.0)
            response.raise_for_status()
            temp_file.write(response.content)
        temp_file.close()
        return temp_file.name

    async def transcribe_and_segment(self, file_path: str) -> list[dict]:
        return [
            {"start": segment.get("start", 0), "end": segment.get("end", 0), "text": segment.get("text", "").strip()}
            for segment in await self.groq.transcribe(file_path)
        ]
