import asyncio
import os
import sys
import re

# Add apps/api to path so we can import app modules
sys.path.insert(0, r"c:\Users\tusha\Desktop\HACKATHONS\OpenAI\ECHO\apps\api")

from app.config import get_settings
from app.db.client import db_client
from app.services.pinecone_service import PineconeService

async def test_supabase():
    print("--- Testing Supabase / PostgreSQL ---")
    settings = get_settings()
    db_url = settings.database_url
    
    if not db_url and settings.supabase_url:
        # Construct the database URL dynamically if DATABASE_URL is not set
        # Supabase url format: https://[project-ref].supabase.co
        match = re.search(r"https://([^.]+)\.supabase\.co", settings.supabase_url)
        if match:
            project_ref = match.group(1)
            # The password listed in .env comments is @EchoOpenAI99
            # Since '@' is a special character in URLs, we URL-encode it as %40
            password = "%40EchoOpenAI99"
            db_url = f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"
            print(f"No DATABASE_URL found. Constructed DSN from Supabase URL: postgresql://postgres:***@db.{project_ref}.supabase.co:5432/postgres")
    
    if not db_url:
        print("[ERROR] No database URL configured in settings or .env file.")
        return False

    try:
        print("Connecting to database...")
        # Use our constructed db_url for the test client
        original_db_url = settings.database_url
        settings.database_url = db_url
        
        await db_client.connect()
        settings.database_url = original_db_url # restore
        
        if db_client.pool:
            async with db_client.pool.acquire() as conn:
                res = await conn.fetchval("SELECT 1")
                if res == 1:
                    print("[OK] Database connection test passed! Connected successfully.")
                    return True
                else:
                    print(f"[ERROR] Database returned unexpected value: {res}")
        else:
            print("[ERROR] Database pool is not initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
    finally:
        await db_client.disconnect()
    return False

def test_pinecone():
    print("\n--- Testing Pinecone Vector Database ---")
    settings = get_settings()
    if not settings.pinecone_api_key:
        print("[ERROR] No Pinecone API key configured in .env file.")
        return False

    try:
        print(f"Initializing Pinecone client with index '{settings.pinecone_index_name}'...")
        service = PineconeService()
        
        # Test index connection/listing
        indexes = [info["name"] for info in service.pc.list_indexes()]
        print(f"Existing Pinecone indexes: {indexes}")
        
        if service.index_name in indexes:
            print(f"[OK] Pinecone connection test passed! Index '{service.index_name}' exists.")
            desc = service.pc.describe_index(service.index_name)
            print(f"Index description: {desc}")
            return True
        else:
            print(f"[WARNING] Index '{service.index_name}' does not exist yet.")
            print("Attempting to auto-create index via PineconeService...")
            # Trigger index creation logic
            service._ensure_index_exists()
            print(f"[OK] Request to create index '{service.index_name}' sent. (Note: creation may take a moment)")
            return True
    except Exception as e:
        print(f"[ERROR] Failed to connect to Pinecone: {e}")
    return False

async def main():
    print("Starting database verification test...\n")
    db_ok = await test_supabase()
    pc_ok = test_pinecone()
    
    print("\n=== Verification Summary ===")
    print(f"Supabase/PostgreSQL: {'SUCCESS' if db_ok else 'FAILED'}")
    print(f"Pinecone:            {'SUCCESS' if pc_ok else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
