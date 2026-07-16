from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from .config import get_settings

from .routers import sessions, memories, echo, finetune, webhooks, auth, realtime
from .db.client import db_client
from .auth.middleware import AuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB or external connections here
    await db_client.connect()
    yield
    # Clean up here
    await db_client.disconnect()

app = FastAPI(title="Echo API", version="0.1.0", lifespan=lifespan)
settings = get_settings()

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuthMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "mode": "demo" if settings.demo_mode else "live",
        "missing_live_integrations": settings.missing_live_integrations
    }

@app.get("/health/db")
async def health_db():
    if not db_client.pool:
        return {"ok": False, "status": "no pool initialized"}
    try:
        async with db_client.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"ok": True, "status": "connected"}
    except Exception as e:
        return {"ok": False, "status": str(e)}

@app.get("/health/redis")
def health_redis():
    if settings.development_mode:
        return {"ok": True, "status": "development mode, redis bypassed"}
    import redis
    import os
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL", settings.redis_url))
        r.ping()
        return {"ok": True, "status": "connected"}
    except Exception as e:
        return {"ok": False, "status": str(e)}

@app.get("/health/openai")
def health_openai():
    import os
    import httpx
    api_key = os.getenv("OPENAI_API_KEY", settings.openai_api_key)
    if not api_key:
        return {"ok": False, "status": "no api key"}
    
    # We can just check if key is loaded for a lightweight check, 
    # but a real check can query the models endpoint
    try:
        resp = httpx.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=5.0)
        return {"ok": resp.status_code == 200, "status": resp.status_code}
    except Exception as e:
        return {"ok": False, "status": str(e)}

@app.get("/health/pinecone")
def health_pinecone():
    import os
    import httpx
    api_key = os.getenv("PINECONE_API_KEY", settings.pinecone_api_key)
    if not api_key:
        return {"ok": False, "status": "no api key"}
    return {"ok": True, "status": "pinecone api key configured"}

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(memories.router)
app.include_router(echo.router)
app.include_router(finetune.router)
app.include_router(webhooks.router)
app.include_router(realtime.router)
