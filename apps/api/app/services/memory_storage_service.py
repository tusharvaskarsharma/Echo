"""Private Supabase Storage fallback for memories when PostgreSQL is unavailable."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.config import get_settings
from app.models.memory import ConsentLevel, MemoryFragment


class MemoryStorageService:
    bucket = "echo-memories"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
        }

    async def _ensure_bucket(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"{self.settings.supabase_url}/storage/v1/bucket",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"id": self.bucket, "name": self.bucket, "public": False},
        )
        # A duplicate bucket is expected after the first save.
        if response.status_code not in (200, 201, 400, 409):
            response.raise_for_status()

    @staticmethod
    def _path(user_id: str, memory_id: str) -> str:
        return f"{user_id}/{memory_id}.json"

    async def save_conversation(self, user_id: str, content: str) -> MemoryFragment:
        now = datetime.now(timezone.utc)
        memory = MemoryFragment(
            id=str(uuid4()),
            session_id=str(uuid4()),
            subject_id=user_id,
            content=content,
            emotion_tags=["reflection"],
            topics=["voice-session"],
            people_mentioned=[],
            consent_level=ConsentLevel.PRIVATE,
            confidence_score=0.7,
            created_at=now,
        )
        path = self._path(user_id, str(memory.id))
        payload = memory.model_dump(mode="json")
        async with httpx.AsyncClient(timeout=30) as client:
            await self._ensure_bucket(client)
            response = await client.post(
                f"{self.settings.supabase_url}/storage/v1/object/{self.bucket}/{path}",
                headers={**self.headers, "Content-Type": "application/json", "x-upsert": "false"},
                content=json.dumps(payload),
            )
            response.raise_for_status()
        return memory

    async def list_memories(self, user_id: str) -> list[MemoryFragment]:
        async with httpx.AsyncClient(timeout=30) as client:
            await self._ensure_bucket(client)
            response = await client.post(
                f"{self.settings.supabase_url}/storage/v1/object/list/{self.bucket}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"prefix": f"{user_id}/", "limit": 100, "sortBy": {"column": "created_at", "order": "desc"}},
            )
            response.raise_for_status()
            entries = response.json()
            memories: list[MemoryFragment] = []
            for entry in entries:
                name = entry.get("name", "")
                if not name.endswith(".json"):
                    continue
                file_response = await client.get(
                    f"{self.settings.supabase_url}/storage/v1/object/{self.bucket}/{user_id}/{name}",
                    headers=self.headers,
                )
                if file_response.is_success:
                    memories.append(MemoryFragment.model_validate(file_response.json()))
        return memories

    async def update_consent(self, user_id: str, memory_id: str, consent: ConsentLevel) -> MemoryFragment:
        path = self._path(user_id, memory_id)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.settings.supabase_url}/storage/v1/object/{self.bucket}/{path}",
                headers=self.headers,
            )
            if response.status_code == 404:
                raise ValueError("Memory not found")
            response.raise_for_status()
            memory = MemoryFragment.model_validate(response.json()).model_copy(update={"consent_level": consent})
            upload = await client.post(
                f"{self.settings.supabase_url}/storage/v1/object/{self.bucket}/{path}",
                headers={**self.headers, "Content-Type": "application/json", "x-upsert": "true"},
                content=json.dumps(memory.model_dump(mode="json")),
            )
            upload.raise_for_status()
        return memory

    async def delete_all(self, user_id: str) -> None:
        """Permanently remove this user's legacy fallback memory objects.

        These JSON objects are only used when PostgreSQL was unavailable, but
        they can contain the same private transcript content as canonical
        database memories.  A memory erasure must therefore clean them too.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.settings.supabase_url}/storage/v1/object/list/{self.bucket}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"prefix": f"{user_id}/", "limit": 1000},
            )
            # A user may never have used the offline fallback, so its bucket
            # need not exist.  There is nothing to erase in that case.
            if response.status_code == 404:
                return
            response.raise_for_status()
            paths = [
                f"{user_id}/{entry['name']}"
                for entry in response.json()
                if isinstance(entry, dict) and entry.get("name", "").endswith(".json")
            ]
            if not paths:
                return
            deletion = await client.delete(
                f"{self.settings.supabase_url}/storage/v1/object/{self.bucket}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"prefixes": paths},
            )
            deletion.raise_for_status()
