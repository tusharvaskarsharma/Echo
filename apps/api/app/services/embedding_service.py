import logging
import asyncio
from openai import AsyncOpenAI
from app.config import get_settings
from app.models.memory import MemoryFragment

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.model = "text-embedding-3-large"

    def serialize_memory(self, memory: MemoryFragment) -> str:
        """
        Serializes a memory into a rich semantic string format, matching the exact prompt template.
        """
        topics = ", ".join(memory.topics) if memory.topics else "None"
        people = ", ".join(memory.people_mentioned) if memory.people_mentioned else "None"
        emotions = ", ".join(memory.emotion_tags) if memory.emotion_tags else "None"
        era = memory.time_period if memory.time_period else "Unknown"
        
        return (
            f"[MEMORY] {memory.content}\n"
            f"[EMOTION] {emotions}\n"
            f"[TOPICS] {topics}\n"
            f"[PEOPLE] {people}\n"
            f"[ERA] {era}"
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Calls OpenAI embeddings API with retries and batching.
        Generates 3072-dimensional embeddings.
        """
        if not texts:
            return []
            
        retries = 3
        for attempt in range(retries):
            try:
                response = await self.client.embeddings.create(
                    input=texts,
                    model=self.model,
                    dimensions=3072
                )
                # Sort by index to ensure order matches input
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [d.embedding for d in sorted_data]
            except Exception as e:
                logger.error(f"Embedding failed on attempt {attempt + 1}/{retries}: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return []
