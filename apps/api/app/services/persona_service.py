class PersonaService:
    def build_prompt(self, subject_name: str, persona_details: dict, memories: list[dict]) -> str:
        """
        Builds the 3-layer persona prompt for the RAG response.
        """
        # Layer 1: Persona Anchor
        anchor = (
            f"You are acting as {subject_name}. "
            f"Age: {persona_details.get('age', 'Unknown')}. "
            f"Speaking Style: {persona_details.get('style', 'Warm, thoughtful, and nostalgic')}."
        )
        
        # Layer 2: Retrieved Memories
        memory_texts = []
        for i, mem in enumerate(memories):
            content = mem.get("content", "")
            topics = ", ".join(mem.get("topics", []))
            time_period = mem.get("time_period", "Unknown era")
            memory_texts.append(f"[MEMORY {i+1}]\n{content}\n[ERA] {time_period}\n[TOPICS] {topics}")
            
        memories_layer = "\n\n".join(memory_texts) if memory_texts else "No memories retrieved."
        
        # Layer 3: Strict Rules
        rules = """
You may ONLY answer using these memories.
Never invent facts.
Never speculate.
If the answer is unavailable, politely say so exactly like this: "I don't have a memory of that — I wish I did."
"""
        
        prompt = f"{anchor}\n\nRETRIEVED MEMORIES:\n{memories_layer}\n\nRULES:\n{rules}"
        return prompt
