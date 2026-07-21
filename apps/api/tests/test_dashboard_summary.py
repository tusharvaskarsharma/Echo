import asyncio

from app.routers.profile import get_dashboard_summary


class DashboardSummaryConnection:
    async def fetchrow(self, query: str, user_id: str) -> dict[str, int]:
        assert "status = 'completed'" in query
        assert "FROM public.memories" in query
        assert user_id == "user-1"
        return {"session_count": 1, "memory_count": 6}


def test_dashboard_summary_counts_only_completed_recordings() -> None:
    result = asyncio.run(get_dashboard_summary({"sub": "user-1"}, DashboardSummaryConnection()))

    assert result == {"session_count": 1, "memory_count": 6}
