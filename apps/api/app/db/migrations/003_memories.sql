-- 003_memories.sql
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    emotion_tags JSONB DEFAULT '[]'::jsonb,
    topics JSONB DEFAULT '[]'::jsonb,
    people_mentioned JSONB DEFAULT '[]'::jsonb,
    consent_level TEXT NOT NULL, -- e.g., 'private', 'family', 'legacy'
    confidence_score NUMERIC NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_subject_id ON memories(subject_id);

COMMENT ON TABLE memories IS 'Stores extracted memory fragments from a session.';
