"""Evidence-bound contract for the persistent ECHO Mind Model."""

from typing import Any
from pydantic import BaseModel, Field, field_validator


class EvidenceBase(BaseModel):
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)


class ValueItem(EvidenceBase):
    value: str = Field(min_length=1)


class BeliefItem(EvidenceBase):
    belief: str = Field(min_length=1)


class PersonalityItem(EvidenceBase):
    trait: str = Field(min_length=1)


class DecisionPattern(EvidenceBase):
    pattern: str = Field(min_length=1)


class LifeLesson(EvidenceBase):
    lesson: str = Field(min_length=1)


class Interest(EvidenceBase):
    topic: str = Field(min_length=1)


class EmotionalPattern(EvidenceBase):
    trigger: str = Field(min_length=1)
    response: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)


class RelationshipItem(EvidenceBase):
    person: str = Field(min_length=1)
    relationship: str = Field(min_length=1)
    sentiment: str = Field(min_length=1)


class GoalItem(EvidenceBase):
    goal: str = Field(min_length=1)
    status: str = Field(min_length=1)


class CommunicationStyle(BaseModel):
    tone: str = ""
    humor: str = ""
    formality: str = ""
    empathy: str = ""
    confidence: float = Field(default=0, ge=0, le=1)


class MindIdentity(BaseModel):
    life_roles: list[str] = Field(default_factory=list)
    core_identity: list[str] = Field(default_factory=list)
    self_description: list[str] = Field(default_factory=list)


class MindModelOutput(BaseModel):
    identity: MindIdentity = Field(default_factory=MindIdentity)
    values: list[ValueItem] = Field(default_factory=list)
    beliefs: list[BeliefItem] = Field(default_factory=list)
    personality: list[PersonalityItem] = Field(default_factory=list)
    communication_style: CommunicationStyle = Field(default_factory=CommunicationStyle)
    decision_patterns: list[DecisionPattern] = Field(default_factory=list)
    emotional_patterns: list[EmotionalPattern] = Field(default_factory=list)
    life_lessons: list[LifeLesson] = Field(default_factory=list)
    relationships: list[RelationshipItem] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    goals: list[GoalItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    mind_summary: str = ""

    @field_validator("mind_summary")
    @classmethod
    def summary_has_safe_length(cls, value: str) -> str:
        words = value.split()
        if value and not 200 <= len(words) <= 400:
            raise ValueError("mind_summary must be 200 to 400 words when supplied")
        return value

    def evidence_ids(self) -> set[str]:
        groups: list[list[Any]] = [self.values, self.beliefs, self.personality, self.decision_patterns, self.emotional_patterns, self.life_lessons, self.relationships, self.interests, self.goals]
        return {memory_id for group in groups for item in group for memory_id in item.evidence}

    def validate_evidence(self, valid_memory_ids: set[str]) -> None:
        unsupported = self.evidence_ids() - valid_memory_ids
        if unsupported:
            raise ValueError(f"Mind Model contains unknown evidence IDs: {sorted(unsupported)}")


class StructuredMemoryInput(BaseModel):
    id: str
    content: str
    semantic_metadata: dict[str, Any] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    people_mentioned: list[str] = Field(default_factory=list)
    emotion_tags: list[str] = Field(default_factory=list)
    time_period: str | None = None
