import asyncpg
from fastapi import Request
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
            raise

    async def run_migrations(self, conn: asyncpg.Connection):
        import os
        logger.info("Running database migrations...")
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.exists(migrations_dir):
            return
            
        sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        for sql_file in sql_files:
            file_path = os.path.join(migrations_dir, sql_file)
            with open(file_path, "r", encoding="utf-8") as f:
                sql = f.read()
            try:
                await conn.execute(sql)
                logger.info(f"Executed migration: {sql_file}")
            except Exception as e:
                logger.error(f"Failed to execute migration {sql_file}: {e}")
                # We don't raise here strictly to prevent breaking startup if a table exists (unless proper tracking is in place)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")

db_client = DatabaseClient()

async def get_db() -> asyncpg.Connection:
    """Dependency injection function for FastAPI routes."""
    if not db_client.pool:
        raise RuntimeError("Database pool is not initialized")
    
    async with db_client.pool.acquire() as connection:
        yield connection
