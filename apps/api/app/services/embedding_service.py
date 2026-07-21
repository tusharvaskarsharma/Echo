import asyncio
from collections import OrderedDict
from hashlib import sha256
import logging
from typing import ClassVar

import httpx

from app.config import get_settings
from app.models.memory import MemoryFragment

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Gemini embeddings kept at 3072 dimensions for the existing Pinecone index."""

    _cache: ClassVar[OrderedDict[str, list[float]]] = OrderedDict()
    _cache_limit: ClassVar[int] = 256

    def __init__(self):
        self.settings = get_settings()

    def serialize_memory(self, memory: MemoryFragment) -> str:
        # The semantic processor deliberately provides the sole embedding text.
        # Never decorate it with source labels or unrelated database fields.
        if memory.search_document:
            return memory.search_document
        topics = ", ".join(memory.topics) if memory.topics else "None"
        people = ", ".join(memory.people_mentioned) if memory.people_mentioned else "None"
        emotions = ", ".join(memory.emotion_tags) if memory.emotion_tags else "None"
        era = memory.time_period if memory.time_period else "Unknown"
        return f"[MEMORY] {memory.content}\n[EMOTION] {emotions}\n[TOPICS] {topics}\n[PEOPLE] {people}\n[ERA] {era}"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        keys = [sha256(text.encode("utf-8")).hexdigest() for text in texts]
        missing: list[tuple[str, str]] = []
        seen_missing: set[str] = set()
        for key, text in zip(keys, texts):
            if key in self._cache:
                self._cache.move_to_end(key)
            elif key not in seen_missing:
                missing.append((key, text))
                seen_missing.add(key)

        if not missing:
            logger.debug("Embedding cache hit for %d texts", len(texts))
            return [list(self._cache[key]) for key in keys]

        payload = {
            "requests": [
                {
                    "model": f"models/{self.settings.gemini_embedding_model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": 3072,
                }
                for _key, text in missing
            ]
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_embedding_model}:batchEmbedContents"
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, params={"key": self.settings.gemini_api_key}, json=payload)
                    response.raise_for_status()
                embeddings = [entry["values"] for entry in response.json()["embeddings"]]
                if len(embeddings) != len(missing) or any(len(vector) != 3072 for vector in embeddings):
                    raise ValueError("Gemini returned unexpected embedding dimensions")
                for (key, _text), vector in zip(missing, embeddings):
                    self._cache[key] = list(vector)
                    self._cache.move_to_end(key)
                while len(self._cache) > self._cache_limit:
                    self._cache.popitem(last=False)
                logger.debug("Embedded %d texts (%d cache hits)", len(missing), len(texts) - len(missing))
                return [list(self._cache[key]) for key in keys]
            except Exception as error:
                logger.error("Gemini embedding attempt %s/3 failed: %s", attempt + 1, error)
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        return []
