import logging
import time
from uuid import uuid4
from openai import AsyncOpenAI
from app.config import get_settings
from app.services.retrieval_service import RetrievalService
from app.services.persona_service import PersonaService
from app.services.tts_service import TTSService
from app.models.echo import ConverseResponse, Citation
from datetime import datetime, timezone
import json
import asyncio

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, conn):
        self.conn = conn
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.retrieval_service = RetrievalService()
        self.persona_service = PersonaService()
        self.tts_service = TTSService()

    async def converse_stream(self, echo_id: str, user_id: str, access_level: str, text: str = None, audio_path: str = None):
        start_time = time.time()
        
        # 1. Handle Audio vs Text
        if audio_path:
            with open(audio_path, "rb") as f:
                transcript = await self.client.audio.transcriptions.create(model="whisper-1", file=f)
                text = transcript.text
                
        if not text:
            raise ValueError("Either text or audio must be provided.")
            
        # 2. Fetch subject_id from echo_id
        subject_record = await self.conn.fetchrow("SELECT subject_id, voice_preset, fine_tuned_model FROM echo_profiles WHERE id = $1", echo_id)
        if not subject_record:
            raise ValueError("Echo profile not found.")
            
        subject_id = subject_record["subject_id"]
        voice_preset = subject_record["voice_preset"] or "alloy"
        model = subject_record["fine_tuned_model"] or "gpt-4o-mini"
        
        # 3. Retrieval
        allowed_consent = ["public"]
        if access_level == "family":
            allowed_consent.extend(["family", "private"]) 
            
        memories = await self.retrieval_service.retrieve_memories(
            question=text,
            subject_id=str(subject_id),
            allowed_consent_levels=allowed_consent
        )
        
        queue = asyncio.Queue()
        
        if not memories:
            response_text = "I don't have a memory of that — I wish I did."
            
            async def fallback_stream():
                await queue.put({"type": "text", "text": response_text})
                await queue.put({"type": "sources", "sources": []})
                
                try:
                    audio_b64 = await self.tts_service.generate_speech(response_text, voice=voice_preset)
                    await queue.put({"type": "audio", "audio": audio_b64})
                except Exception as e:
                    logger.error(f"TTS failed: {e}")
                
                await queue.put(None)
                
            asyncio.create_task(fallback_stream())
            return self._stream_generator(queue)
            
        # 4. Persona Prompt
        subject_info = await self.conn.fetchrow("SELECT full_name FROM subjects WHERE id = $1", subject_id)
        subject_name = subject_info["full_name"] if subject_info else "Your Loved One"
        
        system_prompt = self.persona_service.build_prompt(
            subject_name=subject_name,
            persona_details={"style": "Warm, loving, slightly nostalgic"},
            memories=memories
        )
        
        sources = []
        memory_ids = []
        for mem in memories:
            mem_id = mem.get("memory_id")
            if mem_id:
                memory_ids.append(mem_id)
                sources.append(Citation(
                    memory_id=mem_id,
                    excerpt=mem.get("content", "")[:100] + "...",
                    session_id=mem.get("session_id", ""),
                    timestamp=mem.get("time_period", "")
                ))
        
        # 5. LLM Streaming Call
        completion_stream = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            stream=True
        )
        
        async def generate_audio(sentence: str):
            try:
                # small wait so it doesn't slam the API instantly, yielding to other tasks
                await asyncio.sleep(0.01)
                audio_b64 = await self.tts_service.generate_speech(sentence, voice=voice_preset)
                await queue.put({
                    "type": "audio",
                    "audio": audio_b64
                })
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")

        async def read_stream():
            sentence_buffer = ""
            full_text = ""
            
            try:
                async for chunk in completion_stream:
                    content = chunk.choices[0].delta.content or ""
                    if content:
                        full_text += content
                        await queue.put({
                            "type": "text",
                            "text": content
                        })
                        
                        sentence_buffer += content
                        if any(p in content for p in [".", "?", "!", "\n"]):
                            clean_sentence = sentence_buffer.strip()
                            if clean_sentence:
                                asyncio.create_task(generate_audio(clean_sentence))
                            sentence_buffer = ""
                            
                if sentence_buffer.strip():
                    asyncio.create_task(generate_audio(sentence_buffer.strip()))
                    
                await queue.put({
                    "type": "sources",
                    "sources": [s.model_dump() for s in sources]
                })
                
                # Give TTS tasks a moment to queue and finish if short response
                await asyncio.sleep(1)
                await queue.put(None)
                
                latency = int((time.time() - start_time) * 1000)
                token_usage = len(full_text) // 4
                await self.conn.execute("""
                    INSERT INTO conversation_history 
                    (id, echo_profile_id, user_id, question, response, memory_ids, latency_ms, token_usage, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
                """, str(uuid4()), echo_id, user_id, text, full_text, json.dumps(memory_ids), latency, token_usage, datetime.now(timezone.utc))

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                await queue.put(None)

        asyncio.create_task(read_stream())
        return self._stream_generator(queue)
        
    async def _stream_generator(self, queue: asyncio.Queue):
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"
