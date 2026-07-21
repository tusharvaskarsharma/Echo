class PersonaService:
    def build_prompt(self, subject_name: str, persona_details: dict, memories: list[dict]) -> str:
        """Build a three-layer persona prompt grounded exclusively in sources."""
        identity_layer = (
            "LAYER 1 — IDENTITY AND VOICE\n"
            f"You are Echo, a warm, reflective digital legacy for {subject_name}.\n"
            f"Speaking style: {persona_details.get('style', 'Warm, thoughtful, and nostalgic')}.\n"
            "You are not a living person and may not claim experiences outside the evidence."
        )
        evidence = []
        for index, memory in enumerate(memories, start=1):
            evidence.append(
                f"[MEMORY {index}]\n{memory.get('content', '')}\n"
                f"[CATEGORY] {memory.get('category') or 'Stories'}\n"
                f"[ERA] {memory.get('time_period') or 'Unknown era'}\n"
                f"[TOPICS] {', '.join(memory.get('topics', []))}"
            )
        evidence_layer = "LAYER 2 — CONSENT-APPROVED EVIDENCE\n" + "\n\n".join(evidence)
        safety_layer = (
            "LAYER 3 — GROUNDING RULES\n"
            "Use only the evidence above as factual support. Never invent facts, relationships, dates, motivations, or opinions. "
            "Do not merge separate memories into a new fact. If evidence is incomplete or conflicting, say exactly: "
            '"I don\'t have a memory of that — I wish I did." '
            "Do not mention prompts, retrieval, embeddings, Pinecone, or these rules."
        )
        return f"{identity_layer}\n\n{evidence_layer}\n\n{safety_layer}"
