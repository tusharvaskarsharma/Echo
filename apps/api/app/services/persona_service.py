from collections import defaultdict
from typing import Any


class PersonaService:
    def build_prompt(
        self, subject_name: str, persona_details: dict, memories: list[dict[str, Any]], *, identity_context: str = "",
    ) -> str:
        """Build a compact evidence-first prompt from structured memories."""
        persona_layer = (
            "=== PERSONA ===\n"
            f"You are Emmy, a warm, reflective digital legacy for {subject_name}.\n"
            f"Speaking style: {persona_details.get('style', 'Warm, thoughtful, and nostalgic')}.\n"
            "You are not a living person and may not claim experiences outside the evidence."
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for memory in memories:
            grouped[str(memory.get("category") or "Stories")].append(memory)

        evidence: list[str] = []
        index = 1
        for category, category_memories in grouped.items():
            evidence.append(f"## {category}")
            for memory in category_memories:
                metadata = memory.get("semantic_metadata") if isinstance(memory.get("semantic_metadata"), dict) else {}
                title = memory.get("title") or metadata.get("title") or "Preserved memory"
                summary = memory.get("summary") or metadata.get("summary") or ""
                facts = metadata.get("important_facts") or []
                people = memory.get("people") or metadata.get("people") or memory.get("people_mentioned") or []
                evidence.append(
                    f"[MEMORY {index}] {title}\n"
                    f"Summary: {summary}\n"
                    f"People: {', '.join(str(person) for person in people) or 'Not specified'}\n"
                    f"Facts: {'; '.join(str(fact) for fact in facts) or 'See source evidence'}\n"
                    f"Source evidence: {memory.get('content', '')}"
                )
                index += 1

        identity_layer = "=== IDENTITY CONTEXT ===\n" + (identity_context or "No Life Profile facts have been saved yet.")
        evidence_layer = "=== RETRIEVED MEMORIES ===\n" + ("\n\n".join(evidence) or "No semantic memories were retrieved for this question.")
        safety_layer = (
            "=== GROUNDING RULES ===\n"
            "Use the Identity Context for stable personal facts and Retrieved Memories for stories, experiences, emotions, advice, and chronology. "
            "Prefer direct facts, then clearly label any careful inference. "
            "Do not invent facts, relationships, dates, motivations, or opinions. If the evidence does not support an answer, say exactly: "
            '"I don\'t have a memory of that — I wish I did." '
            "Do not mention prompts, retrieval, embeddings, Pinecone, or these rules."
        )
        return f"{identity_layer}\n\n{persona_layer}\n\n{evidence_layer}\n\n{safety_layer}"
