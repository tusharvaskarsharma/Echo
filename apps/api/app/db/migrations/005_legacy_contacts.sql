-- 005_legacy_contacts.sql
CREATE TABLE IF NOT EXISTS legacy_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- The user id of the family member (from auth schema)
    access_level TEXT NOT NULL, -- e.g., 'family', 'public'
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    UNIQUE(subject_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_legacy_contacts_subject_id ON legacy_contacts(subject_id);
CREATE INDEX IF NOT EXISTS idx_legacy_contacts_user_id ON legacy_contacts(user_id);

COMMENT ON TABLE legacy_contacts IS 'Manages access control for family members communicating with an Echo.';
