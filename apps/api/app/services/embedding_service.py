import asyncio
import logging

import httpx

from app.config import get_settings
from app.models.memory import MemoryFragment

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Gemini embeddings kept at 3072 dimensions for the existing Pinecone index."""

    def __init__(self):
        self.settings = get_settings()

    def serialize_memory(self, memory: MemoryFragment) -> str:
        topics = ", ".join(memory.topics) if memory.topics else "None"
        people = ", ".join(memory.people_mentioned) if memory.people_mentioned else "None"
        emotions = ", ".join(memory.emotion_tags) if memory.emotion_tags else "None"
        era = memory.time_period if memory.time_period else "Unknown"
        return f"[MEMORY] {memory.content}\n[EMOTION] {emotions}\n[TOPICS] {topics}\n[PEOPLE] {people}\n[ERA] {era}"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "requests": [
                {
                    "model": f"models/{self.settings.gemini_embedding_model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": 3072,
                }
                for text in texts
            ]
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_embedding_model}:batchEmbedContents"
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, params={"key": self.settings.gemini_api_key}, json=payload)
                    response.raise_for_status()
                embeddings = [entry["values"] for entry in response.json()["embeddings"]]
                if len(embeddings) != len(texts) or any(len(vector) != 3072 for vector in embeddings):
                    raise ValueError("Gemini returned unexpected embedding dimensions")
                return embeddings
            except Exception as error:
                logger.error("Gemini embedding attempt %s/3 failed: %s", attempt + 1, error)
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        return []
