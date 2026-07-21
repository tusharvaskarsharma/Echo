from app.workers.index_memory import _memory_from_row


def test_reindex_normalizes_jsonb_strings_returned_by_asyncpg():
    memory = _memory_from_row({
        "id": "memory-1", "session_id": "session-1", "subject_id": "subject-1", "user_id": "owner-1",
        "content": "A preserved story.", "emotion_tags": '["reflection"]', "topics": '["family"]',
        "people_mentioned": '[]', "consent_level": "private", "confidence_score": 0.8,
        "semantic_metadata": '{}', "search_document": None,
    })

    assert memory.emotion_tags == ["reflection"]
    assert memory.topics == ["family"]
    assert memory.semantic_metadata == {}
