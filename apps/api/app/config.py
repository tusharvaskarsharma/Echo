from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore")

    development_mode: bool = True
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )
    gemini_api_key: str
    gemini_live_model: str = "gemini-3.1-flash-live-preview"
    gemini_embedding_model: str = "gemini-embedding-001"
    groq_api_key: str
    # Configurable because Groq's catalogue and free-tier availability evolve.
    groq_persona_model: str = "llama-3.3-70b-versatile"
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    pinecone_api_key: str
    pinecone_index: str
    pinecone_index_name: str = "echo-memories"
    pinecone_environment: str = "us-east-1"
    @property
    def missing_live_integrations(self) -> list[str]:
        required = {
            "GEMINI_API_KEY": self.gemini_api_key,
            "GROQ_API_KEY": self.groq_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "SUPABASE_JWT_SECRET": self.supabase_jwt_secret,
            "PINECONE_API_KEY": self.pinecone_api_key,
            "PINECONE_INDEX": self.pinecone_index,
        }
        return [name for name, value in required.items() if not value]

    @property
    def cors_origin_list(self) -> list[str]:
        """Return canonical browser origins from Railway's comma-separated setting.

        Railway stores environment values as strings, while an HTTP Origin never
        includes a trailing slash.  Normalising here keeps a value copied from a
        dashboard (for example ``https://app.example.com/``) from silently
        failing the exact-origin CORS match.  The setting intentionally does not
        support ``*`` because this API accepts credentials.
        """
        raw_value = self.cors_origins.strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {"'", '"'}:
            raw_value = raw_value[1:-1].strip()

        origins: list[str] = []
        for candidate in raw_value.split(","):
            origin = candidate.strip().strip("'\"").rstrip("/")
            if not origin:
                continue
            if origin == "*":
                raise ValueError("CORS_ORIGINS cannot contain '*' when credentials are enabled.")

            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
                raise ValueError(f"Invalid CORS origin: {candidate!r}")
            if origin not in origins:
                origins.append(origin)

        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one HTTP(S) origin.")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
