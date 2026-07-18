"""Strict, evidence-only semantic memory extraction for long-term retrieval."""

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


class MemoryEmotion(BaseModel):
    primary: EmotionName
    confidence: float = Field(ge=0, le=1)


class SemanticMemory(BaseModel):
    """The provider contract. Every field is stored as retrieval evidence."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    context: str = Field(min_length=1)
    important_facts: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    topics: list[str] = Field(min_length=3, max_length=10)
    keywords: list[str] = Field(min_length=10, max_length=20)
    emotion: MemoryEmotion
    intent: IntentName
    memory_type: MemoryType
    importance_score: float = Field(ge=0, le=1)
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
You are the Memory Processor for ECHO. Convert the raw conversation transcript
below into ONE structured semantic memory optimized for vector search and
long-term retrieval.

Use only facts explicitly present in the transcript. Do not infer, speculate,
or invent facts, preferences, people, places, dates, motives, or opinions.
Return ONLY a valid JSON object with exactly this schema:
{{
  "title": "", "summary": "", "context": "", "important_facts": [],
  "user_preferences": [], "people": [], "places": [], "topics": [],
  "keywords": [], "emotion": {{"primary": "neutral", "confidence": 0.0}},
  "intent": "", "memory_type": "", "importance_score": 0.0,
  "search_document": ""
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
