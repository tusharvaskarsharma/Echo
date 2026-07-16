-- 002_sessions.sql
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    status TEXT NOT NULL, -- e.g., 'active', 'processing', 'completed'
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_subject_id ON sessions(subject_id);

COMMENT ON TABLE sessions IS 'Stores interview sessions for a specific subject.';
