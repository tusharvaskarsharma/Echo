import json

from pydantic import BaseModel, Field

from app.services.groq_service import GroqService


class ExtractedMemory(BaseModel):
    content: str = Field(description="The core memory or story shared by the subject.")
    emotion_tags: list[str] = Field(description="Emotional tags.")
    topics: list[str] = Field(description="Themes or topics.")
    people_mentioned: list[str] = Field(description="Names or relationships.")
    time_period: str | None = None
    confidence_score: float = Field(description="A value from 0 to 1.")


class MemoryExtractionResponse(BaseModel):
    memories: list[ExtractedMemory]


class MemoryExtractorService:
    def __init__(self):
        self.groq = GroqService()

    async def extract_memories(self, text_chunks: list[dict]) -> list[ExtractedMemory]:
        transcript_text = "\n".join(f"[{chunk['start']:.1f}s - {chunk['end']:.1f}s]: {chunk['text']}" for chunk in text_chunks)
        prompt = f"""
Extract meaningful life memories from this interview transcript. Return JSON only in this shape:
{{"memories":[{{"content":"...","emotion_tags":["..."],"topics":["..."],"people_mentioned":["..."],"time_period":"...","confidence_score":0.0}}]}}
Ignore filler and never invent facts.

Transcript:
{transcript_text}
"""
        raw = await self.groq.complete([
            {"role": "system", "content": "You are a professional biographer extracting structured memories from transcripts."},
            {"role": "user", "content": prompt},
        ], json_mode=True)
        try:
            return MemoryExtractionResponse.model_validate(json.loads(raw)).memories
        except (json.JSONDecodeError, ValueError):
            return []
