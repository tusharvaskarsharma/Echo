-- 004_emmy_profiles.sql
CREATE TABLE IF NOT EXISTS emmy_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    fine_tuned_model TEXT, -- Optional provider model reference
    voice_preset TEXT, -- Voice preset id
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(subject_id)
);

COMMENT ON TABLE emmy_profiles IS 'Stores the synthesized persona settings for a subject.';
