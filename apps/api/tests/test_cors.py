import asyncio

import httpx

from app import main
from app.config import Settings


VERCEL_ORIGIN = "https://echo-web-mocha.vercel.app"


def _settings(cors_origins: str) -> Settings:
    return Settings(
        development_mode=False,
        cors_origins=cors_origins,
        gemini_api_key="test",
        groq_api_key="test",
        database_url="postgresql://test",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="test",
        supabase_anon_key="test",
        supabase_jwt_secret="test",
        pinecone_api_key="test",
        pinecone_index="test",
    )


def test_cors_origins_are_normalised_from_railway_environment_value() -> None:
    settings = _settings(f' "{VERCEL_ORIGIN}/", https://preview.example.com/ ')

    assert settings.cors_origin_list == [VERCEL_ORIGIN, "https://preview.example.com"]


def test_cors_rejects_wildcard_when_credentials_are_enabled() -> None:
    settings = _settings("*")

    try:
        _ = settings.cors_origin_list
    except ValueError as error:
        assert "credentials" in str(error)
    else:  # pragma: no cover - documents the required security invariant.
        raise AssertionError("Wildcard CORS origin was accepted")


def test_vercel_origin_receives_cors_headers_for_preflight_and_auth_errors() -> None:
    async def run_requests() -> list[httpx.Response]:
        # The exported app is the outer CORS wrapper.  Swap only its run-time
        # allow-list for this isolated test; the underlying real routes and
        # middleware stack are exercised without opening a database connection.
        original_origins = main.app.allow_origins
        main.app.allow_origins = [VERCEL_ORIGIN]
        try:
            transport = httpx.ASGITransport(app=main.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                preflight_headers = {
                    "Origin": VERCEL_ORIGIN,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization, Content-Type",
                }
                return [
                    await client.get("/health", headers={"Origin": VERCEL_ORIGIN}),
                    await client.options("/memories", headers=preflight_headers),
                    await client.options("/mind/latest", headers=preflight_headers),
                    await client.get("/memories", headers={"Origin": VERCEL_ORIGIN}),
                    await client.get("/mind/latest", headers={"Origin": VERCEL_ORIGIN}),
                ]
        finally:
            main.app.allow_origins = original_origins

    health, memories_options, mind_options, memories_error, mind_error = asyncio.run(run_requests())

    assert health.status_code == 200
    assert memories_options.status_code == 200
    assert mind_options.status_code == 200
    assert memories_error.status_code in {401, 403}
    assert mind_error.status_code in {401, 403}

    for response in (health, memories_options, mind_options, memories_error, mind_error):
        assert response.headers["access-control-allow-origin"] == VERCEL_ORIGIN
        assert response.headers["access-control-allow-credentials"] == "true"
