"""Validated, explainable output contract for EMMY's Cognitive Engine."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


Intent = Literal["factual_memory", "emotional_support", "advice", "opinion", "storytelling", "reflection", "life_lesson", "relationship", "preference", "identity", "event_recall", "hypothetical", "unknown"]


class ReasoningPlan(BaseModel):
    answer_strategy: str = ""
    facts_to_use: list[str] = Field(default_factory=list)
    values_to_apply: list[str] = Field(default_factory=list)
    beliefs_to_apply: list[str] = Field(default_factory=list)
    personality_traits: list[str] = Field(default_factory=list)
    communication_style: str = ""
    emotional_state: str = ""
    important_relationships: list[str] = Field(default_factory=list)
    timeline_context: str = ""
    possible_conflicts: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class ResponseConstraints(BaseModel):
    should_answer: bool
    should_refuse: bool
    needs_more_context: bool
    reason: str


class CognitiveReasoningPlan(BaseModel):
    intent: Intent
    question_type: str
    required_memories: list[str] = Field(default_factory=list)
    required_traits: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reasoning_plan: ReasoningPlan
    response_constraints: ResponseConstraints
    citations: list[str] = Field(default_factory=list)
    system_prompt_for_persona_model: str

    @model_validator(mode="after")
    def enforce_confidence_gate(self) -> "CognitiveReasoningPlan":
        if self.confidence < 0.65 and (self.response_constraints.should_answer or not self.response_constraints.needs_more_context):
            raise ValueError("confidence below 0.65 must request more context and prevent an answer")
        return self

    def validate_memory_references(self, memory_ids: set[str]) -> None:
        unsupported = set(self.required_memories + self.citations) - memory_ids
        if unsupported:
            raise ValueError(f"Cognitive plan cites unknown memory IDs: {sorted(unsupported)}")
