import os
import json
import uuid
import tempfile
from typing import List
from openai import AsyncOpenAI
from app.config import get_settings
from app.models.memory import MemoryFragment
from app.models.finetune import FinetuneJob
from app.db import repositories
import asyncpg

class FinetuneBuilderService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

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
            
            # 2. Upload to OpenAI
            await repositories.update_finetune_job(self.conn, job_id, {"status": "uploading"})
            with open(dataset_path, "rb") as f:
                openai_file = await self.client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            # 3. Create Fine-tuning Job
            openai_job = await self.client.fine_tuning.jobs.create(
                training_file=openai_file.id,
                model="gpt-4o-mini"
            )
            
            # 4. Update job record
            return await repositories.update_finetune_job(self.conn, job_id, {
                "openai_job_id": openai_job.id,
                "openai_file_id": openai_file.id,
                "status": "running"
            })
            
        except Exception as e:
            await repositories.update_finetune_job(self.conn, job_id, {
                "status": "failed",
                "error_message": str(e)
            })
            raise

    async def _generate_jsonl(self, subject_id: str, memories: List[MemoryFragment]) -> str:
        # We will use GPT-4o-mini to generate conversational pairs from the memories.
        # This acts as our data synthesis engine.
        
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
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            try:
                res = json.loads(completion.choices[0].message.content)
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
