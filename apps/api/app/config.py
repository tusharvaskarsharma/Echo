from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore")

    development_mode: bool = True
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,https://echo-web.vercel.app"
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
    redis_url: str = "redis://localhost:6379/0"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
