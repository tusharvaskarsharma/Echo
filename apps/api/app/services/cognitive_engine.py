"""Evidence-only planning layer that never produces the final persona response."""

import json
import logging
from typing import Any

from app.models.cognitive import CognitiveReasoningPlan
from app.services.groq_service import GroqService

logger = logging.getLogger(__name__)


class CognitiveEngineService:
    def __init__(self):
        self.groq = GroqService()

    async def plan(
        self,
        question: str,
        retrieved_memories: list[dict[str, Any]],
        mind_model: dict[str, Any] | None = None,
        relationship_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        timeline_context: list[dict[str, Any]] | None = None,
    ) -> CognitiveReasoningPlan:
        memory_ids = {str(memory["id"]) for memory in retrieved_memories}
        prompt = f"""
You are ECHO's Cognitive Reasoning Engine. Do not answer the user. Produce only an evidence-grounded JSON plan.
Use only the retrieved memories, Mind Model, relationship context, timeline context, and conversation history below.
Never invent facts or traits. Ignore irrelevant memories. Resolve conflicts by preserving both time-bound viewpoints.
Intent must be factual_memory, emotional_support, advice, opinion, storytelling, reflection, life_lesson, relationship, preference, identity, event_recall, hypothetical, or unknown.
Every required_memories entry and citation must be an exact retrieved memory ID. If confidence is below 0.65, should_answer must be false, needs_more_context true, and the plan must recommend "I don't know enough about this."
The persona prompt must say to never reveal internal reasoning and to admit uncertainty. Return exactly these keys:
intent, question_type, required_memories, required_traits, missing_information, confidence, reasoning_plan, response_constraints, citations, system_prompt_for_persona_model.

Use JSON objects—not strings or arrays—for both `reasoning_plan` and `response_constraints`.
`reasoning_plan` must include an `answer_strategy` string. `response_constraints` must include boolean
`should_answer`, `should_refuse`, `needs_more_context`, plus a `reason` string.

User question: {question}
Retrieved memories: {json.dumps(retrieved_memories, ensure_ascii=False)}
Mind Model: {json.dumps(mind_model or {}, ensure_ascii=False)}
Relationship context: {json.dumps(relationship_context or {}, ensure_ascii=False)}
Timeline context: {json.dumps(timeline_context or [], ensure_ascii=False)}
Conversation history: {json.dumps(conversation_history or [], ensure_ascii=False)}
""".strip()
        logger.info("Starting cognitive plan for %d retrieved memories", len(retrieved_memories))
        try:
            raw = await self.groq.complete(
                [{"role": "system", "content": "Return only valid JSON. Do not expose hidden reasoning."}, {"role": "user", "content": prompt}],
                json_mode=True,
            )
            plan = CognitiveReasoningPlan.model_validate(json.loads(raw))
            plan.validate_memory_references(memory_ids)
            logger.info("Cognitive plan completed should_answer=%s confidence=%.2f", plan.response_constraints.should_answer, plan.confidence)
            return plan
        except Exception:
            # The caller treats planning as an optional enhancement and can
            # still generate a grounded answer from the same evidence.
            logger.exception("Cognitive planning failed")
            raise
