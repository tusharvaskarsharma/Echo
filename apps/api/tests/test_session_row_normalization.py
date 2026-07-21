from app.db.repositories import _session_from_row


def test_session_row_accepts_jsonb_transcript_segments_from_asyncpg():
    session = _session_from_row({
        "id": "session-1", "subject_id": "subject-1", "status": "active",
        "transcript_segments": '[{"start": 0, "end": 2, "text": "A story"}]',
    })

    assert session.transcript_segments == [{"start": 0, "end": 2, "text": "A story"}]
