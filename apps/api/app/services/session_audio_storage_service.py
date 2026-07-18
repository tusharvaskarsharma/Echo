"""Private Supabase Storage support for audio submitted by interview sessions."""

from __future__ import annotations

import httpx

from app.config import get_settings


class SessionAudioStorageService:
    """Stores recordings privately; clients never receive a provider service key or public URL."""

    bucket = "echo-session-audio"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.supabase_url
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }

    async def _ensure_bucket(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"{self.base_url}/storage/v1/bucket",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"id": self.bucket, "name": self.bucket, "public": False},
        )
        if response.status_code not in (200, 201, 400, 409):
            response.raise_for_status()

    @staticmethod
    def _path(user_id: str, session_id: str, suffix: str) -> str:
        safe_suffix = suffix if suffix in {"webm", "m4a", "wav", "mp3", "ogg"} else "webm"
        return f"{user_id}/{session_id}/recording.{safe_suffix}"

    async def upload(self, user_id: str, session_id: str, content: bytes, content_type: str) -> str:
        suffix = content_type.split("/")[-1].split(";")[0].replace("x-", "")
        path = self._path(user_id, session_id, suffix)
        async with httpx.AsyncClient(timeout=90) as client:
            await self._ensure_bucket(client)
            response = await client.post(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"},
                content=content,
            )
            response.raise_for_status()
        # Persist an opaque storage URI. The worker resolves it using its own
        # service-role credential; there is no public or expiring URL in the DB.
        return f"supabase://{self.bucket}/{path}"

    async def download(self, storage_uri: str) -> bytes:
        prefix = f"supabase://{self.bucket}/"
        if not storage_uri.startswith(prefix):
            raise ValueError("Unexpected session-audio storage URI")
        path = storage_uri.removeprefix(prefix)
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.get(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.content
