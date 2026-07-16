-- 006_conversation_history.sql
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    echo_profile_id UUID NOT NULL REFERENCES echo_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- The user interacting with the Echo
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    memory_ids JSONB DEFAULT '[]'::jsonb, -- Array of memory UUIDs referenced
    latency_ms INTEGER NOT NULL,
    token_usage INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_history_profile_id ON conversation_history(echo_profile_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user_id ON conversation_history(user_id);

COMMENT ON TABLE conversation_history IS 'Logs interactions between family members and an Echo profile.';
