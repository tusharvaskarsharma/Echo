"""Build a consent-gated, traceable cognitive model from structured memories."""

import json

from app.models.mind_model import MindModelOutput, StructuredMemoryInput
from app.services.groq_service import GroqService


class MindModelBuilderService:
    def __init__(self):
        self.groq = GroqService()

    async def build(self, memories: list[StructuredMemoryInput]) -> MindModelOutput:
        if not memories:
            return MindModelOutput(uncertainties=["No structured memories are available yet."])

        evidence = [memory.model_dump(mode="json") for memory in memories]
        prompt = f"""
You are the Mind Model Builder for EMMY. Transform the supplied structured memories into a persistent cognitive model.
Use only traits directly supported by the memories; never infer or invent beliefs, values, preferences, personality, or relationships.
Ignore greetings, filler, and isolated events.

Return JSON only with exactly these keys: identity, values, beliefs, personality, communication_style, decision_patterns,
emotional_patterns, life_lessons, relationships, interests, goals, uncertainties, mind_summary.

Values have value, confidence, evidence; beliefs have belief, confidence, evidence; personality has trait, confidence, evidence.
Decision patterns have pattern, confidence, evidence; life lessons have lesson, confidence, evidence; interests have topic, confidence, evidence.
Every emotional pattern has trigger, response, confidence, evidence. Relationships have person, relationship, sentiment, confidence, evidence.
Goals have goal, status, confidence, evidence. Evidence is an array of source memory IDs and must contain only IDs supplied below.
Confidence is 0 to 1. Put weak candidates in uncertainties instead of asserting them. Leave unsupported categories empty.
Communication style must be empty/default unless repeatedly demonstrated. mind_summary must be an evidence-only 200-400 word summary,
or an empty string when there is not enough evidence for a reliable summary.

Structured memories:
{json.dumps(evidence, ensure_ascii=False)}
""".strip()
        raw = await self.groq.complete(
            [
                {"role": "system", "content": "Return only valid evidence-bound JSON. Never fabricate traits."},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
        )
        model = MindModelOutput.model_validate(json.loads(raw))
        model.validate_evidence({memory.id for memory in memories})
        return model
