from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore")

    development_mode: bool = True  # When True, tasks run synchronously (no Redis/Celery needed)
    # Keep the development origins explicit.  Using "*" is incompatible with
    # credentialed browser requests and would mask deployment configuration bugs.
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,https://echo-web.vercel.app"
    )
    openai_api_key: str
    openai_realtime_model: str = "gpt-realtime-2.1"
    openai_persona_model: str = "gpt-4.1-mini"
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    pinecone_api_key: str
    pinecone_index: str
    pinecone_index_name: str = "echo-memories"
    pinecone_environment: str = "us-east-1"
    redis_url: str = "redis://localhost:6379/0"

    @property
    def openai_model(self) -> str:
        """Alias for openai_persona_model — used by memory_extractor and other services."""
        return self.openai_persona_model

    @property
    def missing_live_integrations(self) -> list[str]:
        required = {
            "OPENAI_API_KEY": self.openai_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "SUPABASE_JWT_SECRET": self.supabase_jwt_secret,
            "PINECONE_API_KEY": self.pinecone_api_key,
            "PINECONE_INDEX": self.pinecone_index,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
