"""Strict, evidence-only semantic memory extraction for long-term retrieval."""

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.groq_service import GroqService


EmotionName = Literal[
    "happy", "sad", "angry", "excited", "anxious", "curious", "neutral",
    "reflective", "frustrated", "grateful",
]
IntentName = Literal[
    "greeting", "question", "planning", "storytelling", "emotional_support",
    "brainstorming", "learning", "reflection", "casual_chat", "problem_solving",
]
MemoryType = Literal[
    "conversation", "preference", "goal", "event", "relationship", "knowledge",
    "experience", "reminder",
]
MemoryCategory = Literal[
    "Identity", "Family", "Childhood", "Career", "Relationships", "Values",
    "Stories", "Advice", "Preferences", "Legacy",
]
ImportanceLevel = Literal["critical", "high", "medium", "low"]


class MemoryEmotion(BaseModel):
    primary: EmotionName
    confidence: float = Field(ge=0, le=1)


class SemanticMemory(BaseModel):
    """The provider contract. Every field is stored as retrieval evidence."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    context: str = Field(min_length=1)
    category: MemoryCategory = "Stories"
    important_facts: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    time_reference: str | None = None
    topics: list[str] = Field(min_length=3, max_length=10)
    keywords: list[str] = Field(min_length=10, max_length=20)
    emotion: MemoryEmotion
    intent: IntentName
    memory_type: MemoryType
    importance_score: float = Field(ge=0, le=1)
    importance_level: ImportanceLevel = "medium"
    search_document: str = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def title_must_be_ten_words_or_fewer(cls, value: str) -> str:
        value = value.strip()
        if len(value.split()) > 10:
            raise ValueError("title must contain at most 10 words")
        return value


class ExtractedMemory(BaseModel):
    """Compatibility shape for the existing database and processing worker."""

    content: str
    emotion_tags: list[str]
    topics: list[str]
    people_mentioned: list[str]
    time_period: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    search_document: str
    semantic_metadata: dict

    @classmethod
    def from_semantic_memory(cls, memory: SemanticMemory) -> "ExtractedMemory":
        metadata = memory.model_dump(mode="json")
        # `content` remains concise and safe for the current memory card and
        # family-source UI. The richer retrieval document is embedded separately.
        return cls(
            content=memory.summary,
            emotion_tags=[memory.emotion.primary],
            topics=memory.topics,
            people_mentioned=memory.people,
            confidence_score=memory.emotion.confidence,
            search_document=memory.search_document,
            semantic_metadata=metadata,
        )


class IndexedSemanticMemory(SemanticMemory):
    """A semantic memory matched to one immutable story unit supplied by Emmy."""

    source_index: int = Field(ge=0)


class SemanticMemoryBatch(BaseModel):
    memories: list[IndexedSemanticMemory] = Field(default_factory=list)


class MemoryExtractorService:
    """Ask Groq for one validated semantic memory from a session transcript."""

    def __init__(self):
        self.groq = GroqService()

    async def extract_memories(self, text_chunks: list[dict]) -> list[ExtractedMemory]:
        transcript_text = "\n".join(
            f"[{chunk['start']:.1f}s - {chunk['end']:.1f}s]: {chunk['text']}"
            for chunk in text_chunks
            if chunk.get("text")
        ).strip()
        if not transcript_text:
            return []

        prompt = f"""
You are the Memory Processor for EMMY. Convert the raw conversation transcript
below into ONE structured semantic memory optimized for vector search and
long-term retrieval.

Use only facts explicitly present in the transcript. Do not infer, speculate,
or invent facts, preferences, people, places, dates, motives, or opinions.
Return ONLY a valid JSON object with exactly this schema:
{{
  "title": "", "summary": "", "context": "", "category": "Stories", "important_facts": [],
  "user_preferences": [], "people": [], "places": [], "objects": [], "time_reference": null, "topics": [],
  "keywords": [], "emotion": {{"primary": "neutral", "confidence": 0.0}},
  "intent": "", "memory_type": "", "importance_score": 0.0,
  "importance_level": "medium", "search_document": ""
}}

Constraints:
- title has at most 10 words; summary is 2 to 5 factual sentences.
- topics has 3 to 10 entries; keywords has 10 to 20 semantic terms and may
  include truthful synonyms.
- emotion.primary must be one of: happy, sad, angry, excited, anxious,
  curious, neutral, reflective, frustrated, grateful.
- intent must be one of: greeting, question, planning, storytelling,
  emotional_support, brainstorming, learning, reflection, casual_chat,
  problem_solving.
- memory_type must be one of: conversation, preference, goal, event,
  relationship, knowledge, experience, reminder.
- category must be Identity, Family, Childhood, Career, Relationships,
  Values, Stories, Advice, Preferences, or Legacy.
- importance_level must be critical, high, medium, or low.
- search_document is the only text embedded. Write it as one natural paragraph
  combining the title, summary, context, facts, preferences, topics, keywords,
  emotion, and intent. Do not include JSON, timestamps, speaker labels, or a
  turn-by-turn transcript.

Transcript:
{transcript_text}
""".strip()

        raw = await self.groq.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "Return schema-valid JSON only. Evidence must be explicit "
                        "in the transcript; omit unsupported details."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
        )
        try:
            semantic_memory = SemanticMemory.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            # A malformed or unsupported provider response is deliberately not
            # persisted; storing invented or partial memories is worse than a retry.
            return []
        return [ExtractedMemory.from_semantic_memory(semantic_memory)]

    async def extract_structured_memories(self, story_units: list[str]) -> dict[int, ExtractedMemory]:
        """Enrich independent interview stories in small concurrent batches.

        The transcript stays authoritative in ``sessions.transcript``.  This
        method produces only metadata for each already-separated story, so the
        model can never merge facts from unrelated answers into one memory.
        """
        indexed_units = [(index, text.strip()) for index, text in enumerate(story_units) if text and text.strip()]
        if not indexed_units:
            return {}

        async def extract_batch(batch: list[tuple[int, str]]) -> dict[int, ExtractedMemory]:
            sources = "\n\n".join(f"SOURCE {index}:\n{text}" for index, text in batch)
            prompt = f"""
You are EMMY's structured memory processor. Each SOURCE below is a single,
complete interview question-and-answer or life story. Return a JSON object:
{{"memories": [ ... ]}}. Create at most one record per SOURCE and never merge
facts between sources. Omit a source only when it contains no personal fact.

Every record must have source_index, title, summary, context, category,
important_facts, user_preferences, people, places, objects, time_reference,
topics, keywords, emotion, intent, memory_type, importance_score,
importance_level, and search_document. Use only explicit evidence. The
search_document must include the concise summary, facts, people, category,
keywords, and the source's original answer in natural language.

Categories: Identity, Family, Childhood, Career, Relationships, Values,
Stories, Advice, Preferences, Legacy.
Importance: critical for identity/immediate family/life-defining values;
high for major events, achievements, regrets, career, and relationships;
medium for meaningful preferences; low only for minor details.

{sources}
""".strip()
            try:
                raw = await self.groq.complete(
                    [
                        {"role": "system", "content": "Return schema-valid JSON only. Never infer facts."},
                        {"role": "user", "content": prompt},
                    ],
                    json_mode=True,
                )
                parsed = SemanticMemoryBatch.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValueError):
                return {}
            allowed = {index for index, _text in batch}
            return {
                memory.source_index: ExtractedMemory.from_semantic_memory(memory)
                for memory in parsed.memories
                if memory.source_index in allowed
            }

        # Eight units keeps prompt sizes modest while allowing independent
        # provider requests to overlap, substantially reducing ingest latency.
        batches = [indexed_units[index:index + 8] for index in range(0, len(indexed_units), 8)]
        results = await asyncio.gather(*(extract_batch(batch) for batch in batches), return_exceptions=True)
        extracted: dict[int, ExtractedMemory] = {}
        for result in results:
            if isinstance(result, dict):
                extracted.update(result)
        return extracted
