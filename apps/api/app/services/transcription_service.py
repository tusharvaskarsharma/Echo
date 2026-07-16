import httpx
import tempfile
import os
from openai import AsyncOpenAI
from app.config import get_settings

class TranscriptionService:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def download_audio(self, audio_url: str) -> str:
        """Downloads audio from a URL to a temporary file and returns the path."""
        if not audio_url or audio_url == "mock_url":
            # For demonstration purposes, if there is no audio URL, we might throw an error or handle it.
            raise ValueError("No valid audio URL provided for transcription.")
            
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=30.0)
            response.raise_for_status()
            with open(temp_file.name, 'wb') as f:
                f.write(response.content)
                
        return temp_file.name

    async def transcribe_and_segment(self, file_path: str) -> list[dict]:
        """
        Sends the audio to Whisper API, requests verbose_json.
        Returns a list of semantic chunks (segments) with timestamps.
        """
        with open(file_path, "rb") as audio_file:
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
            
        # Whisper verbose_json returns 'segments' which are already naturally chunked by pauses/sentences.
        chunks = []
        if hasattr(transcript, 'segments'):
            for segment in transcript.segments:
                chunks.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
        elif isinstance(transcript, dict) and 'segments' in transcript:
            for segment in transcript['segments']:
                chunks.append({
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": segment['text'].strip()
                })
        
        return chunks
