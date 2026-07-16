-- 004_echo_profiles.sql
CREATE TABLE IF NOT EXISTS echo_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    fine_tuned_model TEXT, -- Reference to OpenAI model id
    voice_preset TEXT, -- Voice preset id
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(subject_id)
);

COMMENT ON TABLE echo_profiles IS 'Stores the synthesized persona settings for a subject.';
