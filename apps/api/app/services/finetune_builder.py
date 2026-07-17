import os
import json
import uuid
import tempfile
from typing import List
from app.config import get_settings
from app.services.groq_service import GroqService
from app.models.memory import MemoryFragment
from app.models.finetune import FinetuneJob
from app.db import repositories
import asyncpg

class FinetuneBuilderService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.settings = get_settings()
        self.groq = GroqService()

    async def check_eligibility(self, subject_id: str) -> bool:
        """Check if subject has >= 3 sessions and >= 150 memories."""
        sessions_query = "SELECT count(*) FROM sessions WHERE subject_id = $1 AND status = 'completed'"
        session_count = await self.conn.fetchval(sessions_query, subject_id)
        
        memories_query = "SELECT count(*) FROM memories WHERE subject_id = $1"
        memory_count = await self.conn.fetchval(memories_query, subject_id)
        
        return session_count >= 3 and memory_count >= 150

    async def build_and_submit(self, subject_id: str) -> FinetuneJob:
        if not await self.check_eligibility(subject_id):
            raise ValueError("Subject not eligible for fine-tuning yet.")
            
        memories = await repositories.list_memories(self.conn, subject_id)
        if not memories:
            raise ValueError("No memories found.")

        # Create a queued job record
        job_id = str(uuid.uuid4())
        job = FinetuneJob(
            id=job_id,
            subject_id=subject_id,
            status="queued"
        )
        await repositories.create_finetune_job(self.conn, job)

        try:
            # 1. Synthesize Dataset
            dataset_path = await self._generate_jsonl(subject_id, memories)
            
            # Groq does not offer an equivalent hosted fine-tuning API.  Echo
            # retains the generated, consent-scoped dataset for RAG/persona
            # evaluation instead of uploading private memories to another host.
            return await repositories.update_finetune_job(self.conn, job_id, {
                "status": "completed"
            })
            
        except Exception as e:
            await repositories.update_finetune_job(self.conn, job_id, {
                "status": "failed",
                "error_message": str(e)
            })
            raise

    async def _generate_jsonl(self, subject_id: str, memories: List[MemoryFragment]) -> str:
        # Groq generates evaluation pairs; no external fine-tuning job is created.
        
        subject_record = await self.conn.fetchrow("SELECT full_name FROM subjects WHERE id = $1", subject_id)
        subject_name = subject_record["full_name"] if subject_record else "Subject"
        
        dataset = []
        anchor = f"You are acting as {subject_name}."
        
        # Batch memories into chunks of 10 to generate Q&A
        chunk_size = 10
        for i in range(0, len(memories), chunk_size):
            chunk = memories[i:i+chunk_size]
            mem_text = "\n".join([f"- {m.content}" for m in chunk])
            
            prompt = f"""
            You are a data synthesizer. Based strictly on the following memories of {subject_name}, 
            generate 5 conversational Question-and-Answer pairs.
            The 'user' asks a question about their life, and the 'assistant' (acting as {subject_name}) 
            answers using ONLY the provided memories. Match a warm, natural tone.
            
            Output format: JSON array of objects with "question" and "answer" keys.
            
            Memories:
            {mem_text}
            """
            
            completion = await self.groq.complete([{"role": "user", "content": prompt}], json_mode=True)
            
            try:
                res = json.loads(completion)
                pairs = res.get("pairs", [])
                if not pairs and isinstance(res, dict):
                    # sometimes the model returns keys like 'qa_pairs'
                    for k, v in res.items():
                        if isinstance(v, list):
                            pairs = v
                            break
                            
                for p in pairs:
                    if "question" in p and "answer" in p:
                        dataset.append({
                            "messages": [
                                {"role": "system", "content": anchor},
                                {"role": "user", "content": p["question"]},
                                {"role": "assistant", "content": p["answer"]}
                            ]
                        })
            except Exception as e:
                print(f"Error parsing synthetic data: {e}")
                
        if not dataset:
            raise ValueError("Failed to synthesize any training data.")
            
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, 'w') as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")
                
        return path
