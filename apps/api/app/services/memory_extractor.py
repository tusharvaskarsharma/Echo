from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from app.config import get_settings

class ExtractedMemory(BaseModel):
    content: str = Field(description="The core memory or story shared by the subject.")
    emotion_tags: list[str] = Field(description="List of emotional tags (e.g. 'joy', 'nostalgia').")
    topics: list[str] = Field(description="List of themes or topics discussed.")
    people_mentioned: list[str] = Field(description="Names or relationships of people mentioned.")
    time_period: str | None = Field(description="The period of life this memory is from (e.g. 'childhood', '1980s').", default=None)
    confidence_score: float = Field(description="Confidence score between 0 and 1 that this is a meaningful memory.")

class MemoryExtractionResponse(BaseModel):
    memories: list[ExtractedMemory]

class MemoryExtractorService:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def extract_memories(self, text_chunks: list[dict]) -> list[ExtractedMemory]:
        """
        Takes a list of transcript chunks and uses GPT-4o to extract structured memories.
        """
        # Combine chunks into a single readable format with timestamps to provide context
        transcript_text = "\n".join([f"[{c['start']:.1f}s - {c['end']:.1f}s]: {c['text']}" for c in text_chunks])
        
        prompt = f"""
        Analyze the following interview transcript and extract any meaningful life memories, stories, or reflections.
        For each distinct memory, provide the core content, emotional tags, topics, people mentioned, time period, and your confidence score.
        Ignore small talk or filler conversation.
        
        Transcript:
        {transcript_text}
        """
        
        response = await self.client.beta.chat.completions.parse(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a professional biographer extracting structured memories from transcripts."},
                {"role": "user", "content": prompt}
            ],
            response_format=MemoryExtractionResponse
        )
        
        if not response.choices or not response.choices[0].message.parsed:
            return []
            
        return response.choices[0].message.parsed.memories
