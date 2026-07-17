import asyncpg
from fastapi import HTTPException, Request
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

class DatabaseClient:
    def __init__(self):
        self.pool = None

    async def connect(self):
        settings = get_settings()
        
        # In production (Railway), DATABASE_URL is standard.
        # Fallback to SUPABASE_URL if present.
        db_url = settings.database_url or settings.supabase_url
        if not db_url:
            logger.warning("No DATABASE_URL or SUPABASE_URL found in settings. Database connection skipped.")
            return

        try:
            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
            logger.info("Successfully connected to PostgreSQL.")
            
            # Connection testing and run migrations
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                logger.info("Database connection test passed.")
                await self.run_migrations(conn)
        except Exception as e:
            logger.error(f"Failed to connect to the database: {e}")
            if not settings.development_mode:
                raise
            logger.warning("DEVELOPMENT_MODE=true — continuing without database. DB-dependent routes will fail at request time.")
            self.pool = None

    async def run_migrations(self, conn: asyncpg.Connection):
        import os
        logger.info("Running database migrations...")
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.exists(migrations_dir):
            return
            
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        for sql_file in sql_files:
            already_applied = await conn.fetchval(
                "SELECT 1 FROM public.schema_migrations WHERE filename = $1", sql_file
            )
            if already_applied:
                continue
            file_path = os.path.join(migrations_dir, sql_file)
            with open(file_path, "r", encoding="utf-8") as f:
                sql = f.read()
            try:
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO public.schema_migrations (filename) VALUES ($1)", sql_file
                    )
                logger.info(f"Executed migration: {sql_file}")
            except Exception as e:
                logger.error(f"Failed to execute migration {sql_file}: {e}")
                raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")

db_client = DatabaseClient()

async def get_db() -> asyncpg.Connection:
    """Dependency injection function for FastAPI routes."""
    if not db_client.pool:
        raise HTTPException(
            status_code=503,
            detail="Memory storage is unavailable because the database connection is not configured or reachable.",
        )
    
    async with db_client.pool.acquire() as connection:
        yield connection


async def get_optional_db() -> asyncpg.Connection | None:
    """Return a connection when PostgreSQL is available.

    Local development can use Supabase Auth while the direct database hostname
    is unavailable (for example, on IPv4-only networks). Read-only dashboard
    endpoints use this dependency so they can return an empty owned collection
    instead of leaking an internal 500 error.
    """
    if not db_client.pool:
        yield None
        return

    async with db_client.pool.acquire() as connection:
        yield connection
